from Rules.rules_abc import Rule

class TestRule(Rule):

    def check_status(self):
        print("Test Rule, Checking Status...\n")

        return True

    def take_action(self):
        print("Test Rule, Taking Action...\n")
