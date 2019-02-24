from django.conf import settings
from firefence.backends import Fence
from firefence.rules import Rule


office_vpn_rules = []

for ip in getattr(settings, 'GIFT_CERTIFICATE_IP_WHITELIST', []):
    office_vpn_rules.append(Rule(action=Rule.ALLOW, host=ip))

office_vpn_fence = Fence(office_vpn_rules)
