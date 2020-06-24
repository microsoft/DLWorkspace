#!/usr/bin/env python3

# Label key for repair state
# (IN_SERVICE, OUT_OF_POOL, READY_FOR_REPAIR, IN_REPAIR, AFTER_REPAIR)
REPAIR_STATE = "REPAIR_STATE"

# Annotation key for the last update time of the repair state
REPAIR_STATE_LAST_UPDATE_TIME = "REPAIR_STATE_LAST_UPDATE_TIME"

# Annotation key for unhealthy rules
REPAIR_UNHEALTHY_RULES = "REPAIR_UNHEALTHY_RULES"

# Annotation key for whether the node is in repair cycle.
# An unschedulable node that is not in repair cycle can be manually repaired
# by administrator without repair cycle interruption.
REPAIR_CYCLE = "REPAIR_CYCLE"

# Annotation key for repair message - what phase the node is undergoing
REPAIR_MESSAGE = "REPAIR_MESSAGE"
