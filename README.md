# BLE experiments

```
# setup
python -mvenv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

## Aranet4

Capture "smart home integrations" broadcast packages in passive mode.

```
$ sudo systemctl edit bluetooth.service

# add --experimental to enable passive monitoring

[Service]
ExecStart=
ExecStart=/usr/lib/bluetooth/bluetoothd --experimental

$ sudo systemctl restart bluetooth.service
```
