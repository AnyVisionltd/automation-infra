import asyncio
import concurrent


async def and_wait_if_cancelled(method, loop):
    '''
    This will run the method shielded (ie even if the task is cancelled the inside logic will finish)
    and in the case of the method being cancelled, will wait for the task to finish before
    raising the CancelledError.

    This is useful for cases where say we want to create a
    vm but if the request is cancelled we need to wait for it to finish
    being created before destroying it.
    '''
    try:
        work_task = loop.create_task(method())
        _shield = await asyncio.shield(work_task)
    except concurrent.futures._base.CancelledError as e:
        await work_task
        raise
    return work_task.result()