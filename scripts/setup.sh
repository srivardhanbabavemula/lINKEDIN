#!/bin/bash
# Setup for GitHub Codespaces / Linux
set -e
cd "$(dirname "$0")/.."

echo "=== LinkedIn Networking Copilot Setup (Linux) ==="

python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — edit with YOUR_NAME, MY_SCHOOL, etc. (no LinkedIn login needed in cloud)"
fi

python copilot.py init
python copilot.py seed

cd dashboard/nextjs-app
npm install
cd ../..

echo ""
echo "Setup complete!"
echo ""
echo "Run in Codespaces:"
echo "  source .venv/bin/activate"
echo "  python copilot.py run --no-llm"
echo "  cd dashboard/nextjs-app && npm run dev"
echo ""
echo "Open the PORTS tab and click port 3000 (dashboard)"
echo ""
echo "LinkedIn login/scrape only works on your laptop — use CSV import here."
