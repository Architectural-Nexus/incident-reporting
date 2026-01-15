# Setting Up SSH Key for GitHub Repository Access

## Step 1: Generate SSH Key on Your Server

SSH into your server and generate a new SSH key (or use an existing one):

```bash
ssh root@incidents.archnexus.com

# Check if you already have SSH keys
ls -la ~/.ssh/

# If you don't have a key, generate one:
ssh-keygen -t ed25519 -C "incidents.archnexus.com"
# Press Enter to accept default location (~/.ssh/id_ed25519)
# You can set a passphrase or leave it empty (less secure but easier for automation)

# If you prefer RSA (older systems):
# ssh-keygen -t rsa -b 4096 -C "incidents.archnexus.com"
```

## Step 2: Display Your Public Key

```bash
# Display the public key
cat ~/.ssh/id_ed25519.pub

# Or if you used RSA:
# cat ~/.ssh/id_rsa.pub
```

**Copy the entire output** - it should look like:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... incidents.archnexus.com
```

## Step 3: Add Key to GitHub

### Option A: Via GitHub Web Interface (Recommended)

1. Go to GitHub: https://github.com/settings/keys
2. Click **"New SSH key"** or **"Add SSH key"**
3. Give it a title (e.g., "incidents.archnexus.com server")
4. Paste your public key into the "Key" field
5. Click **"Add SSH key"**

### Option B: Via GitHub CLI (if installed)

```bash
gh auth login
gh ssh-key add ~/.ssh/id_ed25519.pub --title "incidents.archnexus.com"
```

## Step 4: Test the Connection

On your server, test the GitHub connection:

```bash
ssh -T git@github.com
```

You should see:
```
Hi Architectural-Nexus! You've successfully authenticated, but GitHub does not provide shell access.
```

## Step 5: Clone the Repository

Now you can clone using SSH:

```bash
cd /opt
git clone git@github.com:Architectural-Nexus/incident-reporting.git
# or
git clone ssh://git@github.com/Architectural-Nexus/incident-reporting.git
```

## Alternative: Using Deploy Key (Repository-Specific)

If you only want to give access to this specific repository:

1. Go to: https://github.com/Architectural-Nexus/incident-reporting/settings/keys
2. Click **"Add deploy key"**
3. Paste your public key
4. Give it a title
5. **Check "Allow write access"** if you want to push changes (optional)
6. Click **"Add key"**

Deploy keys are repository-specific and more secure for server deployments.

## Troubleshooting

### Permission Denied Error

```bash
# Check key permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub

# Test again
ssh -T git@github.com
```

### Wrong Key Being Used

```bash
# Specify the key explicitly
ssh -i ~/.ssh/id_ed25519 -T git@github.com

# Or add to SSH config
nano ~/.ssh/config
```

Add this to `~/.ssh/config`:
```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

### Still Having Issues?

```bash
# Verbose output for debugging
ssh -vT git@github.com

# Check if key is loaded in agent
ssh-add -l
```

## Quick One-Liner Setup (if you have access)

If you can run commands on the server, here's a quick setup:

```bash
# On the server
ssh-keygen -t ed25519 -C "incidents.archnexus.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

Then manually add the output to GitHub.
