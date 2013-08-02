from __future__ import unicode_literals

from balanced import BalancedProcessor
from dummy import DummyProcessor

processor_map = {
    'BALANCED': BalancedProcessor,
    'DUMMY': DummyProcessor,
}