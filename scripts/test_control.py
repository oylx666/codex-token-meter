import unittest
from unittest.mock import patch, call
import control


class ControlTests(unittest.TestCase):
    def test_shutdown_waits_for_both_components(self):
        with patch.object(control,'signal') as signal, patch.object(control,'is_running',side_effect=[True,False,True,False,False]), patch.object(control.time,'sleep'):
            self.assertTrue(control.stop_components(2))
            self.assertEqual(signal.call_args_list[:2],[call('stop-watcher'),call('close-request')])
            self.assertGreater(signal.call_count,2, 'Startup races require repeated notifications')

    def test_timeout_is_failure_not_success(self):
        with patch.object(control,'signal'), patch.object(control,'is_running',return_value=True), patch.object(control.time,'sleep'), patch.object(control.time,'monotonic',side_effect=[0,0,11]):
            self.assertFalse(control.stop_components(10))
