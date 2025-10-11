# Quick setup script
Write-Host "Setting up FixMyHyd Bot..." -ForegroundColor Green

# Check if venv exists
if (!(Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing requirements..." -ForegroundColor Yellow
pip install python-telegram-bot==20.7
pip install python-dotenv
pip install Pillow

# Verify installation
Write-Host "Verifying installation..." -ForegroundColor Yellow
python -c "from telegram.ext import Application; print('✓ Telegram bot installed successfully!')"

Write-Host "Setup complete! Run 'python run.py' to start the bot." -ForegroundColor Green