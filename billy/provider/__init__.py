from __future__ import unicode_literals

from balanced import BalancedProvider
from dummy import DummyProvider

provider_map = {
    'BALANCED': BalancedProvider,
    'DUMMY': DummyProvider

}
