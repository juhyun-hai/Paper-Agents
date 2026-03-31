#!/usr/bin/env python3
"""
Production Setup Script for Paper Agent
Run this script to prepare the system for deployment to many users.
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path

def check_requirements():
    """Check if all required packages are installed."""
    print("🔍 Checking requirements...")

    required_packages = [
        "fastapi", "slowapi", "uvicorn", "psutil",
        "sentence-transformers", "requests", "pydantic"
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print(f"📦 Install with: pip install {' '.join(missing)}")
        return False

    print("✅ All required packages installed")
    return True

def setup_directories():
    """Create necessary directories for production."""
    print("📁 Setting up directories...")

    directories = [
        "logs",
        "data/cache",
        "data/embeddings",
        "data/pdfs",
        "data/feedback"
    ]

    try:
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {dir_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create directories: {e}")
        return False

def optimize_database():
    """Run database optimizations."""
    print("🗄️ Optimizing database...")

    try:
        # Add parent directory to path for imports
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from src.database.db_manager import PaperDBManager
        from src.utils.config import load_config

        config = load_config()
        db_path = config["database"]["path"]

        if not os.path.exists(db_path):
            print("❌ Database not found. Run daily collection first.")
            return False

        db = PaperDBManager(db_path)
        db.optimize_for_production()

        # Check database size
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"📊 Database size: {size_mb:.1f} MB")

        if size_mb > 500:
            print("⚠️  WARNING: Database is large. Consider PostgreSQL migration for better performance.")

        print("✅ Database optimized")
        return True

    except Exception as e:
        print(f"❌ Database optimization failed: {e}")
        return False

def setup_environment():
    """Setup environment configuration."""
    print("🔧 Setting up environment...")

    env_file = ".env"
    env_example = ".env.example"

    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            print(f"📋 Copying {env_example} to {env_file}")
            with open(env_example, 'r') as f:
                content = f.read()
            with open(env_file, 'w') as f:
                f.write(content)
        else:
            print("❌ No .env.example file found")
            return False

    print("✅ Environment file ready")
    print(f"📝 Please edit {env_file} with your production settings:")
    print("  - Set ENVIRONMENT=production")
    print("  - Configure CORS_ORIGINS for your domain")
    print("  - Set up external API keys if needed")

    return True

def check_system_resources():
    """Check if system has adequate resources for production."""
    print("💻 Checking system resources...")

    try:
        import psutil

        # Check memory
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        print(f"  📊 RAM: {memory_gb:.1f} GB")

        if memory_gb < 2:
            print("⚠️  WARNING: Low memory. Recommend 4GB+ for production")

        # Check disk space
        disk = psutil.disk_usage('.')
        disk_gb = disk.free / (1024**3)
        print(f"  💾 Free disk space: {disk_gb:.1f} GB")

        if disk_gb < 10:
            print("⚠️  WARNING: Low disk space. Papers and embeddings need ~1GB/1000 papers")

        # Check CPU
        cpu_count = psutil.cpu_count()
        print(f"  ⚡ CPU cores: {cpu_count}")

        print("✅ System resources checked")
        return True

    except Exception as e:
        print(f"❌ Could not check system resources: {e}")
        return False

def build_frontend():
    """Build frontend for production."""
    print("🎨 Building frontend...")

    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False

    try:
        # Check if npm is available
        subprocess.run(["npm", "--version"], capture_output=True, check=True)

        # Build frontend
        subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            check=True,
            capture_output=True
        )

        # Check if dist directory was created
        dist_dir = frontend_dir / "dist"
        if dist_dir.exists():
            print("✅ Frontend built successfully")
            return True
        else:
            print("❌ Frontend build failed - no dist directory")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Frontend build failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ npm not found. Install Node.js first.")
        return False

def main():
    """Main setup function."""
    print("🚀 Paper Agent Production Setup")
    print("=" * 40)

    success = True

    # Run all setup steps
    success &= check_requirements()
    success &= setup_directories()
    success &= setup_environment()
    success &= optimize_database()
    success &= check_system_resources()
    success &= build_frontend()

    print("\n" + "=" * 40)

    if success:
        print("🎉 Production setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Edit .env with your production settings")
        print("2. Run: uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        print("3. Set up reverse proxy (nginx) for HTTPS")
        print("4. Configure process manager (systemd/supervisor)")
        print("5. Set up monitoring and backups")

        print("\n⚠️  Production Checklist:")
        print("- [ ] Configure HTTPS/SSL")
        print("- [ ] Set up database backups")
        print("- [ ] Configure log rotation")
        print("- [ ] Set up monitoring (health checks)")
        print("- [ ] Test rate limiting")
        print("- [ ] Review CORS origins")

    else:
        print("❌ Production setup failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()