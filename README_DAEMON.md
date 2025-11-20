# Continuous Market Analysis Setup

## Quick Start

Run the daemon to continuously analyze markets:

```bash
# Start the daemon (runs forever)
PYTHONPATH=. python bin/qs_daemon.py --mode both

# Or just the continuous scanner
PYTHONPATH=. python bin/qs_scanner.py --interval 300
```

## What It Does

The daemon continuously:
- ✅ Scans markets every 5 minutes (configurable)
- ✅ Detects buy/sell signals
- ✅ Monitors price movements (>5% moves)
- ✅ Detects volume spikes (>2x average)
- ✅ Checks for options anomalies
- ✅ Sends SMS alerts automatically
- ✅ Runs daily flow at scheduled time (default: 9 AM)
- ✅ Performs periodic market scans

## Configuration

### Command Line Options

```bash
# Full daemon with all features
python bin/qs_daemon.py --mode both \
    --scan-interval 300 \
    --daily-time 09:00 \
    --scan-schedule 15 \
    --alerts-schedule 30

# Scanner only (continuous)
python bin/qs_scanner.py --interval 300 --signal-threshold 0.7

# Scheduler only (scheduled tasks)
python bin/qs_daemon.py --mode scheduler --daily-time 09:00
```

### Environment Variables

Set in `.env`:
- `TWILIO_ACCOUNT_SID` - For SMS alerts
- `TWILIO_AUTH_TOKEN` - For SMS alerts
- `TWILIO_FROM` - Twilio phone number
- `TWILIO_ALLOWED_NUMBERS` - Comma-separated phone numbers

## Running as a Service (Linux)

### Using systemd

1. Copy the service file:
```bash
sudo cp qs_daemon.service /etc/systemd/system/
```

2. Edit the service file:
```bash
sudo nano /etc/systemd/system/qs_daemon.service
```
Update paths and user.

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable qs_daemon
sudo systemctl start qs_daemon
```

4. Check status:
```bash
sudo systemctl status qs_daemon
sudo journalctl -u qs_daemon -f
```

### Using screen/tmux

```bash
# Start in screen
screen -S qs_daemon
PYTHONPATH=. python bin/qs_daemon.py --mode both
# Press Ctrl+A then D to detach

# Reattach later
screen -r qs_daemon
```

### Using nohup

```bash
nohup PYTHONPATH=. python bin/qs_daemon.py --mode both > qs_daemon.log 2>&1 &
```

## Monitoring

### Logs

Logs are written to:
- `./logs/qs_daemon.log` (if specified)
- Console output

### Check Status

```bash
# Check if running
ps aux | grep qs_daemon

# View recent scans
tail -f logs/qs_daemon.log | grep "Scan #"
```

## Alerts

The system automatically sends SMS alerts for:
- 🔥 Strong buy signals (score > threshold)
- 📉 Sell signals (score < -threshold)
- 📈 Significant price movements (>5%)
- 📊 Volume spikes (>2x average)
- ⚠️ Options anomalies

## Stopping

```bash
# If running in foreground: Ctrl+C

# If running as service:
sudo systemctl stop qs_daemon

# If running in background:
pkill -f qs_daemon
```

## Troubleshooting

### Daemon not starting
- Check Python path: `PYTHONPATH=. python bin/qs_daemon.py --mode both`
- Check logs: `tail -f logs/qs_daemon.log`
- Verify database exists: `ls -la data/qs.duckdb`

### No alerts being sent
- Verify Twilio credentials in `.env`
- Check `TWILIO_ALLOWED_NUMBERS` is set
- Test SMS manually: `python bin/qs_alerts.py --check-signals --send-sms`

### High CPU usage
- Increase scan interval: `--scan-interval 600` (10 minutes)
- Disable options checking: `--no-options`
- Reduce scan frequency: `--scan-schedule 30`

