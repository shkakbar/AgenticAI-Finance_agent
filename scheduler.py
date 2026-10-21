import schedule
import time
from datetime import datetime
from main import main
from config import SCHEDULE_TIMES

def run_with_timestamp():
    print(f"\n{'='*80}")
    print(f"⏰ Scheduled run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    main()

def setup_schedule():
    print("⏰ Setting up automated schedule...")
    print()
    
    for market, times in SCHEDULE_TIMES.items():
        for schedule_time in times:
            schedule.every().day.at(schedule_time['time']).do(run_with_timestamp)
            print(f"  ✓ {schedule_time['label']}: {schedule_time['time']}")
    
    print()
    print("✅ Schedule configured. Press Ctrl+C to stop.")

if __name__ == "__main__":
    setup_schedule()
    print("🚀 Running initial analysis...")
    run_with_timestamp()
    
    while True:
        schedule.run_pending()
        time.sleep(60)