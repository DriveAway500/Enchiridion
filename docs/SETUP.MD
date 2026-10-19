# Installation Guide (Arch Linux)

This guide walks you through installing the bot and everything it needs, step by step. You do not need to be an expert: just copy and paste each command into your terminal, in order, and read the notes if something goes wrong.

## Overview

The project has two parts:

1. **Omega-Api**: the API the bot talks to. It has its own manual.
2. **The bot**: this project, which includes a Rust library called `chart-lib` (inside `Enchiridion/`) that must be compiled once.

You will do the following, in this order:

1. Install the system tools
2. Install and set up Omega-Api
3. Create a Python virtual environment and install the requirements
4. Build chart-lib with Maturin
5. Install the required font
6. Set up Docker (optional, you do it yourself)
7. Run the bot

## Before you start

You need:

- A computer running Arch Linux (or an Arch-based distribution)
- Internet access
- A user account with `sudo` permission

All commands below are meant to be run in a terminal. Lines starting with `#` are comments: they only explain things and you do not need to type them.

## Step 1: Install the system tools

Update your system and install Git, Python, the compiler tools and Rust:

```bash
sudo pacman -Syu
sudo pacman -S --needed git python python-pip base-devel rust
```

Check that everything is installed:

```bash
git --version
python --version
rustc --version
```

Each command should print a version number. If one says "command not found", repeat the install command above.

## Step 2: Install Omega-Api

The bot needs the API to work, so you must set it up first.

Clone the API repository:

```bash
git clone https://github.com/DriveAway500/Omega-Api.git
cd Omega-Api
```

Now open the file named `README.md` inside the `Omega-Api` folder (or its manual) and follow its instructions until the API is set up and working.

When you are done, go back to your main folder:

```bash
cd ..
```

> **Tip:** Do not continue to the next step until the API is working.

## Step 3: Get the bot and create the virtual environment

Go into the project folder, called `Enchiridion`:

```bash
cd Enchiridion
```

Create a virtual environment. This is a private box where the project's Python packages live, so they do not mess with the rest of your system:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

You should now see `(.venv)` at the beginning of your terminal line. Every time you open a new terminal to work with the bot, you must run the activate command again.

Install the requirements:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This can take a few minutes.

## Step 4: Build chart-lib with Maturin

`chart-lib` is written in Rust and has to be compiled and installed into your virtual environment.

Make sure the virtual environment is still active (you should see `(.venv)` in the terminal). Install Maturin:

```bash
pip install maturin
```

Go to the library folder and build it:

```bash
cd Enchiridion/chart-lib
maturin develop --release
```

The first build may take several minutes. This is normal.

When it finishes, go back to the project's main folder:

```bash
cd ../..
```

> **Note:** `maturin develop` installs the library directly into the active virtual environment, so you do not need to install a wheel file by hand. If you prefer to generate a wheel file instead, run `maturin build --release` inside `Enchiridion/chart-lib` and install the file it creates in `target/wheels/` with `pip install <file-name>.whl`.

## Step 5: Install the required font

The Rust code is not fully configured yet when it comes to fonts, so it expects the DejaVu font to be on your system. On Arch Linux, the package is called `ttf-dejavu` (it is the equivalent of `fonts-dejavu-core` on Debian/Ubuntu):

```bash
sudo pacman -S --needed ttf-dejavu
fc-cache -fv
```

To confirm the font is installed:

```bash
fc-list | grep -i dejavu
```

You should see a list of DejaVu fonts.

## Step 6: Docker (optional)

Docker setup is not covered by this project, so you need to configure it yourself if you want to use it. If you are new to Docker, these are the basic steps on Arch Linux:

```bash
sudo pacman -S --needed docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

After the last command, log out and log back in so the change takes effect. Then test it:

```bash
docker run hello-world
```

For more help, see the [Arch Wiki page on Docker](https://wiki.archlinux.org/title/Docker).

## Step 7: Run the bot

Make sure that:

- Omega-Api is running
- Your virtual environment is active (`(.venv)` is visible)
- You are in the bot's main folder

Then start the bot:

```bash
python main.py
```

## Troubleshooting

| Problem | Likely cause / fix |
| --- | --- |
| `command not found` for `maturin` | Your virtual environment is probably not active. Run `source .venv/bin/activate` from the project folder and try again. |
| Rust or compiler errors while running `maturin develop` | Make sure `rust` and `base-devel` are installed (Step 1). Then run the command again. |
| The charts show missing or broken text | The DejaVu font is probably missing. Repeat Step 5. |
| `ModuleNotFoundError` when starting the bot | The virtual environment is not active, or the requirements were not installed. Activate it and run `pip install -r requirements.txt` again. |
| `permission denied` when using Docker | Run `sudo usermod -aG docker $USER`, then log out and back in. |

## Quick checklist

- [ ] System tools installed (`git`, `python`, `rust`, `base-devel`)
- [ ] Omega-Api installed and running
- [ ] Virtual environment created and active
- [ ] `pip install -r requirements.txt` finished
- [ ] `chart-lib` built with `maturin develop --release`
- [ ] `ttf-dejavu` installed
- [ ] Docker configured (if needed)
- [ ] Bot started