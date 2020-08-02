import logging

import pytest

from webapp import rm_requestor


@pytest.mark.asyncio
async def test_happy_flow():
    """Need to have resource_manager up and running on localhost:9080"""
    rm = dict(endpoint="localhost:9080")
    data = {"host": {}}
    possible = await rm_requestor.theoretically_fulfill(rm, data)
    assert possible
    allocate_result = await rm_requestor.allocate(rm['endpoint'], data)
    assert allocate_result['status'] == 'Success'
    vm_name = allocate_result['info'][0]['name']
    deallocate_result = await rm_requestor.deallocate(vm_name, rm['endpoint'])
    assert deallocate_result['status'] == 'Success'
