import logging
log = logging.getLogger(__name__)


def connect_trigger(event):
    '''
    Utility function that verifies that start trigger is set appropriately
    since some channels may be disabled.

    This needs to be explicitly hooked up in your IOManifest.
    '''
    # Since we want to make sure timing across all engines in the task are
    # synchronized properly, we need to inspect for the active channels and
    # then determine which device task is the one to syncrhonize all other
    # tasks to. We prioritize the last engine (the one that is started last)
    # and prioritize the analog output over the analog input. This logic may
    # change in the future.
    controller = event.workbench.get_plugin('psi.controller')

    ai_channels = []
    ao_channels = []
    ci_channels = []
    co_channels = []
    for engine in list(controller._engines.values())[::-1]:
        hw_ai = engine.get_channels(mode='analog', direction='in', timing='hw', active=True)
        hw_ao = engine.get_channels(mode='analog', direction='out', timing='hw', active=True)
        hw_ci = engine.get_channels(mode='counter', direction='in', timing='hw', active=True)
        hw_co = engine.get_channels(mode='counter', direction='out', timing='hw', active=True)
        ai_channels.extend(hw_ai)
        ao_channels.extend(hw_ao)
        ci_channels.extend(hw_ci)
        co_channels.extend(hw_co)

    # For now, we are ignoring the ci_channels and co_channels.
    channels = ai_channels + ao_channels + ci_channels

    # If no channels are active, we don't have any sync issues.
    if len(channels) == 0:
        log.info('No channels are active.')
        return

    # If only one channel is active, we don't have any sync issues.
    if len(channels) == 1:
        log.info('Only one channel active. Disabling start trigger.')
        channels[0].start_trigger = ''
        return

    # At least with the NI hardware I'm familiar with, counter channels require
    # an external clock (e.g., provided by an analog input our output task).
    # So, we cannot use the co_channel or ci_channel for setting the start trigger.
    if ao_channels:
        c = ao_channels[0]
        direction = 'ao'
    else:
        c = ai_channels[0]
        direction = 'ai'

    dev = c.channel.split('/', 1)[0]
    trigger = f'/{dev}/{direction}/StartTrigger'
    master_engine = None
    for c in channels:
        if dev in c.channel and direction in c.channel:
            log.info(f'Setting {c} start_trigger to ""')
            c.start_trigger = ''
            if master_engine is None:
                master_engine = c.engine
        else:
            log.info(f'Setting {c} start_trigger to "{trigger}"')
            c.start_trigger = trigger

    # Now, make sure the master engine is set to the one that controls the
    # start trigger.
    log.info('Setting master engine to %s', master_engine.name)
    controller._master_engine = master_engine
