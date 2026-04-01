#!/usr/bin/env python3
"""
Setup daily trending collection cron job.
"""

import os
import sys
from crontab import CronTab
from pathlib import Path

def setup_daily_cron():
    """Setup daily trending collection cron job."""
    print("🕐 Setting up daily trending collection...")

    # Get current directory and script paths
    backend_dir = Path(__file__).parent.parent.absolute()
    venv_path = backend_dir / "venv" / "bin" / "python"
    script_path = backend_dir / "scripts" / "daily_trending_collector.py"

    # Create cron job
    cron = CronTab(user=True)

    # Remove existing jobs for trending collection
    cron.remove_all(comment='trending_papers_collection')

    # Create new job to run daily at 6:00 AM
    job = cron.new(command=f'cd {backend_dir} && {venv_path} {script_path}')
    job.hour.on(6)
    job.minute.on(0)
    job.set_comment('trending_papers_collection')

    # Create another job to run at 6:00 PM for evening update
    job_evening = cron.new(command=f'cd {backend_dir} && {venv_path} {script_path}')
    job_evening.hour.on(18)
    job_evening.minute.on(0)
    job_evening.set_comment('trending_papers_collection_evening')

    # Write cron jobs
    cron.write()

    print("✅ Daily trending collection scheduled:")
    print(f"   📅 6:00 AM daily: {venv_path} {script_path}")
    print(f"   📅 6:00 PM daily: {venv_path} {script_path}")
    print("   (Run 'crontab -l' to verify)")

    return True

def setup_systemd_timer():
    """Alternative: Setup systemd timer for systems that prefer it."""
    print("📝 Creating systemd timer for trending collection...")

    backend_dir = Path(__file__).parent.parent.absolute()
    venv_path = backend_dir / "venv" / "bin" / "python"
    script_path = backend_dir / "scripts" / "daily_trending_collector.py"

    # Service file content
    service_content = f"""[Unit]
Description=Research Intelligence - Daily Trending Papers Collection
After=network.target

[Service]
Type=oneshot
User={os.getenv('USER', 'research_agent')}
WorkingDirectory={backend_dir}
Environment=PATH={backend_dir}/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={venv_path} {script_path}
StandardOutput=journal
StandardError=journal
"""

    # Timer file content
    timer_content = """[Unit]
Description=Run trending papers collection twice daily
Requires=research-trending.service

[Timer]
OnCalendar=*-*-* 06:00:00
OnCalendar=*-*-* 18:00:00
Persistent=true

[Install]
WantedBy=timers.target
"""

    # Write files
    service_file = "/tmp/research-trending.service"
    timer_file = "/tmp/research-trending.timer"

    with open(service_file, 'w') as f:
        f.write(service_content)

    with open(timer_file, 'w') as f:
        f.write(timer_content)

    print(f"✅ Systemd service files created:")
    print(f"   📄 {service_file}")
    print(f"   📄 {timer_file}")
    print(f"\n📋 To install (run as root/sudo):")
    print(f"   sudo cp {service_file} /etc/systemd/system/")
    print(f"   sudo cp {timer_file} /etc/systemd/system/")
    print(f"   sudo systemctl daemon-reload")
    print(f"   sudo systemctl enable --now research-trending.timer")

    return True

def main():
    """Main setup function."""
    print("🚀 Research Intelligence - Trending Collection Setup")
    print("=" * 60)

    # Check if we can use crontab
    try:
        from crontab import CronTab
        setup_daily_cron()
        cron_success = True
    except ImportError:
        print("⚠️  python-crontab not available")
        cron_success = False
    except Exception as e:
        print(f"⚠️  Cron setup failed: {e}")
        cron_success = False

    # Always create systemd files as an alternative
    try:
        setup_systemd_timer()
        systemd_success = True
    except Exception as e:
        print(f"⚠️  Systemd timer creation failed: {e}")
        systemd_success = False

    print("\n" + "=" * 60)
    if cron_success:
        print("✅ Cron job setup completed successfully!")
    elif systemd_success:
        print("✅ Systemd timer files created - manual installation required")
    else:
        print("❌ Automatic setup failed - manual configuration required")

    print(f"\n💡 To run trending collection manually:")
    print(f"   cd {Path(__file__).parent.parent}")
    print(f"   source venv/bin/activate")
    print(f"   python scripts/daily_trending_collector.py")

if __name__ == "__main__":
    main()