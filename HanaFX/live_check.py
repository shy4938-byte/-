import sys
from app.verification import live_check
report=live_check(sys.argv[1] if len(sys.argv)>1 else 'live-report',full_month=True)
print('Live bank validation:',report['status'])
raise SystemExit(report['status']!='passed')
