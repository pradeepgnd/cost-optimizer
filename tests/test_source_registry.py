"""Publisher/registration fixtures: conditional writes, conflicts, restarts and readback."""
from io import BytesIO
import json
import re
from types import SimpleNamespace

from botocore.exceptions import ClientError
import httpx
import pytest

from app.adapters.base import SetupIncomplete
from app.adapters.live_zetaris import ZetarisDataLayer, redact_sql
from app.source_contracts import SourceBindings, StorageConfig
from app.source_registry import (AWS_KEY_ID_ENV, AWS_SECRET_ENV, EvidencePublisher, aws_source_credentials,
                                 bundle_plan, put_immutable, register_bundle)
from app.source_snapshots import canonical, digest, json_load
from tests.test_zetaris_adapter import bundle, response_rows, ROOT


class FakeS3:
    def __init__(self):
        self.objects, self.puts = {}, 0

    def put_object(self, *, Bucket, Key, Body, IfNoneMatch=None, IfMatch=None, **kwargs):
        previous = self.objects.get((Bucket,Key))
        if (IfNoneMatch == "*" and previous is not None) or (IfMatch is not None and (previous is None or IfMatch != digest(previous))):
            raise ClientError({"Error": {"Code": "PreconditionFailed"}},"PutObject")
        self.objects[(Bucket,Key)] = Body
        self.puts += 1
        return {"ETag": digest(Body),"VersionId": str(self.puts)}

    def get_object(self, *, Bucket, Key):
        body = self.objects.get((Bucket,Key))
        if body is None:
            raise ClientError({"Error": {"Code": "NoSuchKey"}},"GetObject")
        return {"Body": BytesIO(body),"ETag": digest(body),"VersionId": "fixture-version"}


class FakeZetaris:
    def __init__(self, storage, config):
        self.storage, self.config = storage, config
        self.databases, self.tables, self.queries = set(), {}, []
        self.src, self.last_query_id = config.namespace, "fixture-query"
        self.key, self.org, self.base = "fixture-key","1","https://zetaris.test"
        self.bindings = None
        self.client = SimpleNamespace(get=self.metadata)

    def metadata(self, url, **kwargs):
        table = url.rsplit("/",1)[-1]
        return httpx.Response(200,json={"format": "JSON","path": self.tables[table],"parameters": {"multiLine": "true"}},
                              request=httpx.Request("GET",url))

    def _run_sql(self, sql, limit=50):
        self.queries.append(sql)
        if sql == "SHOW LIGHTNING DATABASES":
            return response_rows([{"name": name} for name in sorted(self.databases)])
        if sql.startswith("SHOW LIGHTNING TABLES"):
            return response_rows([{"name": name} for name in self.tables])
        if sql.startswith("CREATE LIGHTNING DATABASE"):
            self.databases.add(sql.split()[3])
            return {"headers": [],"data": []}
        if sql.startswith("CREATE LIGHTNING FILESTORE"):
            table = sql.split()[4]
            self.tables[table] = re.search(r'PATH "([^"]+)"',sql).group(1)
            return {"headers": [],"data": []}
        table = re.search(r" FROM [A-Za-z0-9_]+\.([A-Za-z0-9_]+)",sql).group(1)
        path = self.tables[table]
        bucket, key = path.removeprefix("s3a://").split("/",1)
        rows = json_load(self.storage.objects[(bucket,key)])
        if "COUNT(*)" in sql:
            return response_rows([{"record_count": str(len(rows))}])
        match = re.search(r"record_id = '([^']+)'",sql)
        if match:
            rows = [row for row in rows if row["record_id"] == match.group(1)]
        return response_rows(rows[:limit])

    def read_evidence(self, record_id):
        return ZetarisDataLayer.read_evidence(self, record_id)


@pytest.fixture
def registry(bundle):
    config = StorageConfig.model_validate_json((ROOT / "data/source_examples/localstack.json").read_text())
    s3 = FakeS3()
    layer = FakeZetaris(s3,config)
    report = register_bundle(layer,bundle[0],config,client=s3)
    bindings = SourceBindings.model_validate(report["bindings"])
    layer.bindings = bindings
    return layer,s3,config,bindings


def test_dry_run_needs_no_clients_or_credentials_and_contains_only_test_credentials(bundle):
    config = StorageConfig.model_validate_json((ROOT / "data/source_examples/localstack.json").read_text())
    plan = bundle_plan(bundle[0],config)
    assert plan["mutations_performed"] is False and plan["mode"] == "dry_run"
    assert len(plan["tables"]) == 3 and all("AWSSECRETACCESSKEY \"test\"" in table["statement"] for table in plan["tables"])


def test_immutable_put_reuses_same_bytes_but_never_overwrites_conflicts():
    s3 = FakeS3()
    assert put_immutable(s3,"bucket","key",b"one")["reused"] is False
    assert put_immutable(s3,"bucket","key",b"one")["reused"] is True
    with pytest.raises(ValueError,match="conflict"):
        put_immutable(s3,"bucket","key",b"two")
    assert s3.puts == 1 and s3.objects[("bucket","key")] == b"one"


def test_registration_reuses_matching_sources_and_preserves_pinned_release(bundle,registry):
    layer,s3,config,bindings = registry
    created = len([sql for sql in layer.queries if sql.startswith("CREATE")])
    puts = s3.puts
    report = register_bundle(layer,bundle[0],config,client=s3)
    assert all(item["state"] == "reused" for item in report["registration"])
    assert all(item["reused"] for item in report["publications"])
    assert s3.puts == puts and len([sql for sql in layer.queries if sql.startswith("CREATE")]) == created
    assert report["bindings"] == bindings.model_dump(mode="json")


def test_registration_conflict_does_not_drop_or_patch_existing_source(bundle,registry):
    layer,s3,config,bindings = registry
    table = bindings.tables["models"]
    layer.tables[table] = "s3a://other-bucket/wrong.json"
    with pytest.raises(ValueError,match="conflict"):
        register_bundle(layer,bundle[0],config,client=s3)
    assert layer.tables[table] == "s3a://other-bucket/wrong.json"
    assert not any(sql.startswith(("DROP","ALTER")) for sql in layer.queries)


def test_evidence_write_readback_idempotency_and_publisher_restart(registry):
    layer,s3,config,bindings = registry
    record = {"id": "fixture-run/sample", "run_id": "fixture-run", "kind": "integration_test_fixture", "payload": {"text": "synthetic", "latency_s": 0.01}}
    first = EvidencePublisher(layer,config,bindings,client=s3).write(record)
    puts = s3.puts
    second = EvidencePublisher(layer,config,bindings,client=s3).write(record)
    assert first.version == second.version and first.content_sha256 == digest(canonical(record))
    assert first.status.value == "unverified" and s3.puts == puts
    payload,ref = layer.read_evidence(record["id"])
    assert payload == record and ref.version == first.version
    with pytest.raises(ValueError,match="conflict"):
        EvidencePublisher(layer,config,bindings,client=s3).write({**record,"payload": {"changed": True}})


def test_second_append_retains_first_record_and_stable_source_version(registry):
    layer,s3,config,bindings = registry
    publisher = EvidencePublisher(layer,config,bindings,client=s3)
    record = {"id": "fixture-run/first", "run_id": "fixture-run", "kind": "integration_test_fixture", "payload": {"x": 1}}
    first = publisher.write(record)
    second = publisher.write({**record,"id": "fixture-run/second"})
    returned,ref = layer.read_evidence(record["id"])
    assert returned == record and first.version == ref.version and second.record_id != first.record_id


def test_publication_cas_conflict_retries_without_losing_other_records(registry):
    layer,s3,config,bindings = registry
    publisher = EvidencePublisher(layer,config,bindings,client=s3)
    original = s3.put_object
    injected = False
    def race(**kwargs):
        nonlocal injected
        if "/evidence/" in kwargs["Key"] and not injected:
            injected = True
            raise ClientError({"Error": {"Code": "PreconditionFailed"}},"PutObject")
        return original(**kwargs)
    s3.put_object = race
    record = {"id": "race-run/first", "run_id": "race-run", "kind": "integration_test_fixture", "payload": {}}
    assert publisher.write(record).record_id == record["id"] and injected


def test_invalid_cross_run_or_oversized_evidence_is_rejected_before_storage(registry):
    layer,s3,config,bindings = registry
    publisher = EvidencePublisher(layer,config,bindings,client=s3)
    puts = s3.puts
    for record in ({"id": "other/first", "run_id": "one", "kind": "feature_sample", "payload": {}},
                   {"id": "one/first", "run_id": "one", "kind": "unsupported", "payload": {}},
                   {"id": "one/first", "run_id": "one", "kind": "feature_sample", "payload": {"text": "x" * (1024*1024)}}):
        with pytest.raises(ValueError):
            publisher.write(record)
    assert s3.puts == puts


def test_reference_scenario_uses_exact_queried_prices_without_execution_tariff_claim():
    from scripts.check_zetaris_sources import reference_projection
    from app.source_contracts import CatalogModel
    from app.contracts import SourceRef
    model = CatalogModel(catalog_id="fixture/reference",name="fixture",input_usd_per_m="0.07",output_usd_per_m="0.20")
    ref = SourceRef(source_set="catalog",record_id=model.catalog_id,version="fixture",query_id="fixture-query")
    result = reference_projection(model,ref)
    assert result["execution_tariff"] is False and result["model_execution_performed"] is False
    assert result["row"]["gross_monthly_usd"] == "0.09" and result["source"]["query_id"] == "fixture-query"
    with pytest.raises(ValueError,match="unknown"):
        reference_projection(model.model_copy(update={"input_usd_per_m": None}),ref)


# AWS: Zetaris reads S3 file stores only with a key in the table OPTIONS. Fixture values below are
# shape-valid fakes, never real credentials.
FAKE_KEY_ID = "AKIAFIXTUREKEY000001"
FAKE_SECRET = "s" * 36 + "/+=A"


def aws_config():
    return StorageConfig(backend="aws", bucket="fixture-bucket", publisher_endpoint=None, zetaris_endpoint=None)


@pytest.fixture
def aws_key(monkeypatch):
    monkeypatch.setenv(AWS_KEY_ID_ENV, FAKE_KEY_ID)
    monkeypatch.setenv(AWS_SECRET_ENV, FAKE_SECRET)


def test_aws_dry_run_shows_placeholders_even_when_a_key_is_set(bundle, aws_key):
    plan = bundle_plan(bundle[0], aws_config())
    text = json.dumps(plan)
    assert FAKE_KEY_ID not in text and FAKE_SECRET not in text
    assert all('AWSACCESSKEYID "<key id>", AWSSECRETACCESSKEY "<secret>"' in t["statement"] for t in plan["tables"])


def test_aws_registration_puts_the_key_only_in_create_statements(bundle, aws_key):
    config, s3 = aws_config(), FakeS3()
    layer = FakeZetaris(s3, config)
    report = register_bundle(layer, bundle[0], config, client=s3)
    creates = [sql for sql in layer.queries if sql.startswith("CREATE LIGHTNING FILESTORE")]
    assert len(creates) == 3
    assert all(f'AWSACCESSKEYID "{FAKE_KEY_ID}", AWSSECRETACCESSKEY "{FAKE_SECRET}"' in sql for sql in creates)
    assert not any(FAKE_SECRET in sql or FAKE_KEY_ID in sql for sql in layer.queries if sql not in creates)
    assert FAKE_SECRET not in json.dumps(report) and FAKE_KEY_ID not in json.dumps(report)
    assert not any(FAKE_SECRET.encode() in body for body in s3.objects.values())


def test_aws_registration_without_a_key_fails_before_any_publication(bundle, monkeypatch):
    monkeypatch.delenv(AWS_KEY_ID_ENV, raising=False)
    monkeypatch.delenv(AWS_SECRET_ENV, raising=False)
    config, s3 = aws_config(), FakeS3()
    layer = FakeZetaris(s3, config)
    with pytest.raises(SetupIncomplete, match=AWS_KEY_ID_ENV):
        register_bundle(layer, bundle[0], config, client=s3)
    assert s3.puts == 0 and layer.queries == []


@pytest.mark.parametrize("key_id,secret", [
    (FAKE_KEY_ID, 'x", PATH "s3a://other-bucket/x'),
    ('AKIA"; DROP DATABASE x', FAKE_SECRET),
    ("ASIA" + "A" * 16, FAKE_SECRET),  # temporary keys need a session token Zetaris options do not carry
])
def test_aws_key_with_the_wrong_shape_is_rejected(monkeypatch, key_id, secret):
    monkeypatch.setenv(AWS_KEY_ID_ENV, key_id)
    monkeypatch.setenv(AWS_SECRET_ENV, secret)
    with pytest.raises(SetupIncomplete, match="malformed"):
        aws_source_credentials()


def test_aws_evidence_table_carries_the_key_and_reads_back(bundle, aws_key):
    config, s3 = aws_config(), FakeS3()
    layer = FakeZetaris(s3, config)
    layer.bindings = SourceBindings.model_validate(register_bundle(layer, bundle[0], config, client=s3)["bindings"])
    record = {"id": "aws-run/sample", "run_id": "aws-run", "kind": "integration_test_fixture", "payload": {"x": 1}}
    ref = EvidencePublisher(layer, config, layer.bindings, client=s3).write(record)
    evidence_create = [sql for sql in layer.queries if sql.startswith("CREATE LIGHTNING FILESTORE TABLE evidence_")]
    assert len(evidence_create) == 1 and f'AWSSECRETACCESSKEY "{FAKE_SECRET}"' in evidence_create[0]
    assert layer.read_evidence(record["id"])[0] == record and ref.record_id == record["id"]


def test_credentials_never_reach_the_trace_or_configuration_ref(monkeypatch):
    for name, value in {"ZETARIS_REST_URL": "https://zetaris.test/api/v1.0", "ZETARIS_ORG_ID": "1",
                        "ZETARIS_API_KEY": "fixture-api-key"}.items():
        monkeypatch.setenv(name, value)
    events = []
    trace = SimpleNamespace(event=lambda *args, **kwargs: events.append((args, kwargs)))
    layer = ZetarisDataLayer(trace=trace)
    layer.client = SimpleNamespace(post=lambda url, **kwargs: httpx.Response(
        200, json={"headers": [], "data": []}, request=httpx.Request("POST", url)))
    statement = ('CREATE LIGHTNING FILESTORE TABLE t FROM ns FORMAT JSON OPTIONS (PATH "s3a://b/k", '
                 'AWSACCESSKEYID "{}", AWSSECRETACCESSKEY "{}")')
    layer._run_sql(statement.format(FAKE_KEY_ID, FAKE_SECRET))
    other_secret = "t" * 36 + "/+=B"
    layer._run_sql(statement.format(FAKE_KEY_ID, other_secret))
    assert events and not any(FAKE_SECRET in repr(e) or FAKE_KEY_ID in repr(e) or other_secret in repr(e) for e in events)
    refs = {e[1]["extra"]["configuration_ref"] for e in events if e[0][1] == "zetaris_query"}
    assert len(refs) == 1  # the hash does not depend on the key
    assert redact_sql(statement.format(FAKE_KEY_ID, FAKE_SECRET)).endswith(
        'AWSACCESSKEYID "...redacted", AWSSECRETACCESSKEY "...redacted")')
