from __future__ import unicode_literals

from balanced import BalancedProcessor
from billy.utils.models import Enum
from .dummy import DummyProcessor


ProcessorType = Enum('BALANCED', 'DUMMY', name='processor_type')

processor_map = {
    ProcessorType.BALANCED: BalancedProcessor,
    ProcessorType.DUMMY: DummyProcessor,
}
