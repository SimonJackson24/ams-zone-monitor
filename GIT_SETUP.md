# Git Repository Setup Guide

## Pushing to GitHub

1. Create a new repository on GitHub (don't initialize with README, .gitignore, or license)
2. Connect your local repository to GitHub:

```bash
# Add the remote repository URL
git remote add origin https://github.com/YOUR-USERNAME/ams-zone-monitor.git

# Push your commits to GitHub
git push -u origin master
```

## Pushing to GitLab

1. Create a new project on GitLab (don't initialize with README)
2. Connect your local repository to GitLab:

```bash
# Add the remote repository URL
git remote add origin https://gitlab.com/YOUR-USERNAME/ams-zone-monitor.git

# Push your commits to GitLab
git push -u origin master
```

## Pushing to Bitbucket

1. Create a new repository on Bitbucket (don't initialize with README)
2. Connect your local repository to Bitbucket:

```bash
# Add the remote repository URL
git remote add origin https://bitbucket.org/YOUR-USERNAME/ams-zone-monitor.git

# Push your commits to Bitbucket
git push -u origin master
```

## Additional Git Commands

```bash
# Check remote repositories
git remote -v

# Create and switch to a new branch
git checkout -b feature-branch

# Push changes to specific branch
git push origin feature-branch

# Pull latest changes
git pull origin master
```
