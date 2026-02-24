def test_logger():
    from amrita_core import logging as lg

    lg.replace_logger_handler(lg.logger, lg.logger_id)
    lg.debug = True
    lg.debug_log("Testing logger")
    lg.debug = False
    lg.logger.debug("EHLO")
    lg.logger.info("Using logger")
