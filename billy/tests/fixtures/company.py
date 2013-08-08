from __future__ import unicode_literals

from models.processor import ProcessorType


def sample_company(
        processor_type=ProcessorType.DUMMY,
        processor_api_key='MY_DUMMY_API_KEY_1',
        is_test=True):
    return dict(
        processor_type=processor_type,
        processor_api_key=processor_api_key,
        is_test=is_test
    )