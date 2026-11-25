"""Regression coverage for the read-only editor debug-print path."""
import struct
import tempfile
import unittest
from pathlib import Path

from authoring_io import sha, write_json
from log_diagnostics import EDITOR_LOG_FORMAT, diagnose


def varint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def field(number, value):
    if isinstance(value, int):
        return varint(number << 3) + varint(value)
    return varint((number << 3) | 2) + varint(len(value)) + value


def envelope(payload):
    return struct.pack('>II', len(payload) + 4, len(payload)) + payload


class EditorDebugLogTests(unittest.TestCase):
    def test_read_prints_page_and_preserve_unmatched_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / 'editor.bytes'
            message = '关卡入口'.encode('utf-8')
            graph = field(22, field(2, message)) + field(7, field(2, 123)) + field(9, 456)
            lua = field(23, field(2, b'client print')) + field(3, 2) + field(4, b'sandbox')
            trace = field(12, field(2, b'unexecuted string literal')) + field(4, 1)
            raw = envelope(field(1, trace) + field(1, graph) + field(1, lua))
            log.write_bytes(raw)
            artifact = root / 'client.lua'
            artifact.write_bytes(b'return 1\n')
            spec = root / 'diagnose.json'
            binary = {'path': log.name, 'format': EDITOR_LOG_FORMAT, 'limit': 1}
            # A supplied artifact binding alone must never match an unbound export.
            config = {
                'schema': 2, 'logs': [binary],
                'bindings': [{'build_id': 'local', 'artifact': artifact.name, 'mapping': None}],
            }
            write_json(spec, config)
            first = diagnose(spec, read_roots=[root])
            self.assertEqual(first['status'], 'not_checked')
            self.assertEqual(first['host'], 'not_checked')
            self.assertEqual(first['inputs'][str(log)], sha(raw))
            self.assertEqual(first['editor_logs'][0]['next_offset'], 1)
            self.assertEqual(first['editor_logs'][0]['ignored_record_count'], 1)
            self.assertEqual(first['editor_logs'][0]['severity'], 'not_checked')
            self.assertEqual(len(first['events']), 1)
            event = first['events'][0]
            self.assertEqual(event['message'], '关卡入口')
            self.assertEqual(event['source_kind'], 'node_graph_print')
            self.assertEqual(event['log_record_index'], 1)
            self.assertEqual(event['graph_id'], '123')
            self.assertEqual(event['entity_id'], '456')
            self.assertEqual(event['binding'], 'unmatched')
            self.assertIsNone(event['artifact_sha256'])
            self.assertEqual(first['groups'], [])

            binary['offset'] = 1
            write_json(spec, config)
            second = diagnose(spec)
            self.assertIsNone(second['editor_logs'][0]['next_offset'])
            self.assertEqual(second['events'][0]['message'], 'client print')
            self.assertEqual(second['events'][0]['source_kind'], 'client_lua_print')
            self.assertEqual(second['events'][0]['session_label'], 'sandbox')
            self.assertEqual(second['events'][0]['elapsed_seconds'], '2')
            self.assertEqual(second['observed_error_count'], 0)
            self.assertEqual(log.read_bytes(), raw)

    def test_reject_ambiguous_or_outside_workspace_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / 'project'
            project.mkdir()
            spec = project / 'diagnose.json'
            log = project / 'editor.bytes'
            config = {'schema': 2, 'logs': [{'path': log.name, 'format': EDITOR_LOG_FORMAT}], 'bindings': []}
            write_json(spec, config)
            print_record = field(22, field(2, b'print'))
            for raw, message in (
                (b'plain text', 'Unsupported editor debug-log envelope'),
                (envelope(field(1, print_record + print_record)), 'Ambiguous editor debug-log field'),
                (
                    envelope(field(1, print_record + field(23, field(2, b'lua')))),
                    'Ambiguous editor debug-log print kind',
                ),
                (envelope(field(1, field(22, field(3, b'missing')))), 'Missing editor debug-log print text'),
                (envelope(field(1, field(22, field(2, b'\xff')))), 'invalid start byte'),
            ):
                with self.subTest(raw=raw):
                    log.write_bytes(raw)
                    with self.assertRaisesRegex(ValueError, message):
                        diagnose(spec, read_roots=[project])

            outside = root / 'outside.bytes'
            outside.write_bytes(envelope(field(1, print_record)))
            for entry in (str(outside), {'path': str(outside), 'format': EDITOR_LOG_FORMAT}):
                config['logs'] = [entry]
                write_json(spec, config)
                with self.assertRaisesRegex(ValueError, 'outside allowed project/output roots'):
                    diagnose(spec, read_roots=[project])
