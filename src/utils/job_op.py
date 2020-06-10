#!/usr/bin/env python3


class JobOp(object):
    def __init__(self, name, past_tense, from_states, to_state):
        self.name = name
        self.past_tense = past_tense
        self.from_states = from_states
        self.to_state = to_state


class KillOp(JobOp):
    def __init__(self, desc):
        from_states = {
            "unapproved",
            "queued",
            "scheduling",
            "running",
            "pausing",
            "paused",
        }
        super().__init__("kill", "killed", from_states, "killing")
        self.desc = desc


class PauseOp(JobOp):
    def __init__(self):
        from_states = {
            "unapproved",
            "queued",
            "scheduling",
            "running",
        }
        super().__init__("pause", "paused", from_states, "pausing")


class ResumeOp(JobOp):
    def __init__(self):
        from_states = {
            "paused",
        }
        super().__init__("resume", "resumed", from_states, "unapproved")


class ApproveOp(JobOp):
    def __init__(self):
        from_states = {
            "unapproved",
        }
        super().__init__("approve", "approved", from_states, "queued")
