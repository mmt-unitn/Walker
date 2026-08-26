# Useful MADS Commands

This document provides a quick reference for monitoring, diagnosing, recording,
and replaying messages with MADS.

## Quick copy-and-paste commands

```bash
mads top --crypto --key_broker=YOUR_BROKER_KEY --key_client=YOUR_CLIENT_KEY --keys_dir=KEYS_DIRECTORY
```

```bash
mads doctor -s YOUR_FILE.ini --graph=NEW_FILE.dot
```

```bash
mads up -f YOUR_FILE.toml 
```

```bash
mads record -o NEW_FILE.bag --crypto --key_broker=YOUR_BROKER_KEY --key_client=YOUR_CLIENT_KEY --keys_dir=KEYS_DIRECTORY
```

```bash
mads play YOUR_FILE.bag --rate RATE
```

## `mads top`

`mads top` displays all active topics, including:

- the message rate in messages per second (`MSG/s`);
- the size of the messages;
- the bandwidth used in bytes per second (`bytes/s`).

When encryption is enabled, provide the broker key, client key, and keys
directory:

```bash
mads top \
  --crypto \
  --key_broker=YOUR_BROKER_KEY \
  --key_client=YOUR_CLIENT_KEY \
  --keys_dir=KEYS_DIRECTORY
```

Example:

```bash
mads top \
  --crypto \
  --key_broker=broker \
  --key_client=monitor \
  --keys_dir=/home/security/keys
```

## `mads doctor`

`mads doctor` performs a diagnostic check and provides a brief description of
any detected problems.

You can pass a MADS configuration file with `-s` and generate a Graphviz DOT
file with `--graph`. The graph describes how the agents are connected and which
messages they send to one another.

```bash
mads doctor -s YOUR_FILE.ini --graph=NEW_FILE.dot
```

Example:

```bash
mads doctor -s system.ini --graph=agents.dot
```

This command reads `system.ini` and writes the resulting connection graph to
`agents.dot`.

## `mads up`

`mads up` launches all the agents defined by the selected TOML launch file. The
agents use the MADS configuration stored in `/usr/local/etc/mads.ini`.

Use `-f` to specify the TOML launch file.

Example using a TOML file from the repository's `launch` directory:

```bash
mads up -f launch/YOUR_FILE.toml
```

Replace `launch/YOUR_FILE.toml` with the path to the required TOML file found
in the repository's `launch` directory.

## `mads record`

`mads record` records the selected topics in a bag file. Use `-o` to specify
the output file. When encryption is enabled, include the crypto options:

```bash
mads record -o NEW_FILE.bag \
  --crypto \
  --key_broker=YOUR_BROKER_KEY \
  --key_client=YOUR_CLIENT_KEY \
  --keys_dir=KEYS_DIRECTORY
```

Example:

```bash
mads record -o session.bag \
  --crypto \
  --key_broker=broker \
  --key_client=recorder \
  --keys_dir=/home/security/keys
```

The generated bag file can later be replayed with `mads play`. Use `--rate` to
control the playback speed:

```bash
mads play YOUR_FILE.bag --rate RATE
```

Example—replay `session.bag` at twice the original speed:

```bash
mads play session.bag --rate 2.0
```

Replace all uppercase placeholders with values appropriate for your system.
