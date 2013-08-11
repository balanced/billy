from __future__ import unicode_literals

from billy.models.processor import ProcessorType


def sample_company(
        processor_type=ProcessorType.DUMMY,
        processor_credential='MY_DUMMY_API_KEY_1',
        is_test=True):
    return dict(
        processor_type=processor_type,
        processor_credential=processor_credential,
        is_test=is_test
    )