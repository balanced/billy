from __future__ import unicode_literals

from balanced import BalancedProcessor
from dummy import DummyProcessor
from utils.models import Enum


ProcessorType = Enum('BALANCED', 'DUMMY', name='processor_type')

processor_map = {
    ProcessorType.BALANCED: BalancedProcessor,
    ProcessorType.DUMMY: DummyProcessor,
}
