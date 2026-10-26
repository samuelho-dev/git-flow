#!/usr/bin/env python3
"""Synthetic native-record privacy fixture, not Terraform/cloud RPC evidence.

Run with python3 -m unittest discover -s tests -p 'test_terraform_plan_diagnostics.py'.
"""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import types
import unittest
from unittest.mock import patch

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/terraform-plan.yml'
# Execute the actual inline implementation, not a copied sanitizer or a source-text assertion.
source = textwrap.dedent(WORKFLOW.read_text().split(
    "python3 - <<'PY_READ_DIAGNOSTICS'\n", 1)[1].split(
    '\n          PY_READ_DIAGNOSTICS', 1)[0])
diagnostic = types.ModuleType('terraform_plan_diagnostics')
exec(compile(source, str(WORKFLOW), 'exec'), diagnostic.__dict__)
CANARY = 'CTK1115_PRIVATE_CANARY'


def native_record(rpc, request_id, boundary, **fields):
    return {
        '@level': 'trace', '@message': boundary,
        '@timestamp': '2026-10-26T01:02:03.000Z' if boundary == 'Received request'
                      else '2026-10-26T01:02:03.250Z',
        'tf_provider_addr': 'registry.terraform.io/hashicorp/aws',
        'tf_req_id': request_id, 'tf_rpc': rpc,
        'request_body': {'password': CANARY},
        'response_body': {'token': CANARY},
        'headers': {'Authorization': 'Bearer ' + CANARY},
        'url': 'https://example.invalid/private?token=' + CANARY,
        'environment': {'AWS_SECRET_ACCESS_KEY': CANARY},
        **fields,
    }


class PlanDiagnosticTest(unittest.TestCase):
    def run_child(self, script, env=None):
        output, errors = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, env or {}, clear=True), redirect_stdout(output), redirect_stderr(errors):
            code = diagnostic.observe([sys.executable, '-u', '-c', script])
        self.assertEqual(errors.getvalue(), '')
        self.assertNotIn(CANARY, output.getvalue())
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_actual_pipe_resource_data_source_none_and_private_sink_exclusion(self):
        cases = (
            ('PlanResourceChange', 'RESOURCE', 'tf_resource_type', 'aws_sqs_queue'),
            ('ReadDataSource', 'DATA_SOURCE', 'tf_data_source_type', 'aws_caller_identity'),
            ('ConfigureProvider', 'NONE', None, None),
        )
        records = []
        for index, (rpc, _, field, concrete_type) in enumerate(cases, 1):
            request_id = f'11111111-1111-4111-8111-{index:012x}'
            concrete = {field: concrete_type} if field else {}
            records.extend(native_record(rpc, request_id, boundary, **concrete)
                           for boundary in ('Received request', 'Served request'))
        child = textwrap.dedent(f'''
            import json, os, sys
            forbidden = ('TF_LOG_PATH', 'TF_LOG_SDK_PROTO_DATA_DIR', 'TF_CLI_ARGS',
                         'TF_CLI_ARGS_plan', 'TF_GRAPH_TRACE', 'TF_REATTACH_PROVIDERS',
                         'GITHUB_OUTPUT', 'GITHUB_STEP_SUMMARY', 'GITHUB_ENV', 'GITHUB_PATH')
            assert all(key not in os.environ for key in forbidden), {CANARY!r}
            assert os.environ['TF_LOG'] == 'JSON', {CANARY!r}
            assert os.environ['TF_LOG_SDK_PROTO'] == 'TRACE', {CANARY!r}
            records = json.loads({json.dumps(records)!r})
            sys.stdout.write({CANARY!r} + '\\n')
            sys.stderr.write('{{"malformed":' + {CANARY!r} + '\\n')
            sys.stdout.write('x' * 70000 + json.dumps(records[0]) + '\\n')
            duplicate = json.dumps(records[0])[:-1] + ',"tf_rpc":"ReadResource"}}'
            sys.stderr.write(duplicate + '\\n')
            for index, record in enumerate(records):
                stream = sys.stdout if index % 2 == 0 else sys.stderr
                stream.write(json.dumps(record) + '\\n')
                stream.flush()
            sys.exit(2)
        ''')
        with tempfile.TemporaryDirectory() as folder:
            paths = {key: str(Path(folder) / key) for key in (
                'TF_LOG_PATH', 'TF_LOG_SDK_PROTO_DATA_DIR', 'GITHUB_OUTPUT',
                'GITHUB_STEP_SUMMARY', 'GITHUB_ENV', 'GITHUB_PATH')}
            code, output = self.run_child(child, {
                **paths, 'TF_CLI_ARGS': '-out=' + folder + '/unwanted-plan',
                'TF_CLI_ARGS_plan': '-out=' + folder + '/unwanted-plan',
                'TF_GRAPH_TRACE': '1', 'TF_REATTACH_PROVIDERS': CANARY,
            })
            self.assertEqual(list(Path(folder).iterdir()), [])
        self.assertEqual(code, 0)
        self.assertEqual(len(output), len(records) + 1)
        for index, record in enumerate(output[:-1]):
            self.assertEqual(record['event'], 'RPC_BEGIN' if index % 2 == 0 else 'RPC_END')
            self.assertEqual(record['provider'], 'AWS')
            expected_rpc, expected_kind, _, concrete_type = cases[index // 2]
            self.assertEqual(record['rpc'], expected_rpc)
            self.assertEqual(record['type_kind'], expected_kind)
            self.assertEqual(record['type_sha256'], hashlib.sha256(concrete_type.encode()).hexdigest()
                             if concrete_type else None)
            if concrete_type:
                self.assertNotIn(concrete_type, json.dumps(record))
            self.assertEqual(record['request_sha256'], hashlib.sha256(
                records[index]['tf_req_id'].encode()).hexdigest())
            self.assertNotIn(records[index]['tf_req_id'], json.dumps(record))
            expected_keys = {'event', 'provider', 'type_kind', 'type_sha256', 'rpc',
                             'request_sha256', 'at_ms'}
            if index % 2:
                expected_keys.add('elapsed_ms')
                self.assertEqual(record['elapsed_ms'], 250)
            self.assertEqual(set(record), expected_keys)
        self.assertEqual(output[-1], {
            'event': 'READ_RPC_SUMMARY', 'observation': 'OBSERVED',
            'begins': 3, 'ends': 3,
            'pending': 0, 'exit_code': 2,
        })

    def test_unknown_malformed_missing_and_failed_records_are_not_success(self):
        request_id = '11111111-1111-4111-8111-000000000001'
        base = native_record('ReadResource', request_id, 'Received request', tf_resource_type=CANARY)
        unknown = [
            {**base, 'tf_rpc': CANARY}, {**base, 'tf_req_id': CANARY},
            {**base, 'tf_provider_addr': CANARY}, {**base, '@timestamp': CANARY},
            {**base, '@message': CANARY}, {**base, 'tf_resource_type': {'secret': CANARY}},
            {'type': 'refresh_start', 'hook': {'resource': CANARY}},
            native_record('ValidateListResourceConfig', request_id, 'Received request',
                          tf_resource_type='aws_first', tf_list_resource_type='aws_second'),
        ]
        for lines, child_exit, observed, pending in (
                (unknown, 0, 'UNVERIFIED', 0),
                ([base], 7, 'OBSERVED', 1),
                ([base, {**base, '@message': 'Served request'}], 7, 'OBSERVED', 0)):
            with self.subTest(child_exit=child_exit, observation=observed, pending=pending):
                child = ('import json,sys; records=json.loads(' + repr(json.dumps(lines))
                         + '); [print(json.dumps(record),flush=True) for record in records]; '
                         + 'sys.exit(' + str(child_exit) + ')')
                code, output = self.run_child(child)
                self.assertEqual(code, 1)
                self.assertEqual(output[-1]['observation'], observed)
                self.assertEqual(output[-1]['pending'], pending)
                self.assertEqual(output[-1]['exit_code'], child_exit)

    def test_observer_error_reaps_its_child_without_printing_exception_or_child_bytes(self):
        class FailFirstWrite(io.StringIO):
            def write(self, value):
                if not getattr(self, 'failed', False):
                    self.failed = True
                    raise OSError(CANARY)
                return super().write(value)

        with tempfile.TemporaryDirectory() as folder:
            acknowledgement = Path(folder) / 'stopped'
            record = native_record('ConfigureProvider',
                                   '11111111-1111-4111-8111-000000000001', 'Received request')
            child = textwrap.dedent(f'''
                import json,signal,sys,time
                from pathlib import Path
                def stopped(_signal, _frame):
                    Path({str(acknowledgement)!r}).write_text('SIGINT')
                    raise SystemExit(0)
                signal.signal(signal.SIGINT, stopped)
                print(json.dumps(json.loads({json.dumps(record)!r})), flush=True)
                time.sleep(60)
            ''')
            output, errors = FailFirstWrite(), io.StringIO()
            with patch.dict(os.environ, {}, clear=True), redirect_stdout(output), redirect_stderr(errors):
                code = diagnostic.observe([sys.executable, '-u', '-c', child])
            self.assertEqual(code, 1)
            self.assertEqual(acknowledgement.read_text(), 'SIGINT')
            self.assertEqual(errors.getvalue(), '')
            self.assertNotIn(CANARY, output.getvalue())
            self.assertEqual(json.loads(output.getvalue()), {
                'event': 'READ_RPC_ERROR', 'reason': 'CHILD_OR_OBSERVER_FAILURE',
            })


if __name__ == '__main__':
    unittest.main()
