# Git Setup Script for Payroll Management System
# This script sets up the Git environment and provides common Git commands

# Add Git to PATH if not already there
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    $env:PATH += ";C:\Program Files\Git\bin"
    Write-Host "Added Git to PATH" -ForegroundColor Green
}

# Configure Git user if not already set
$currentUser = git config --global user.name
if (-not $currentUser) {
    Write-Host "Setting up Git user configuration..." -ForegroundColor Yellow
    git config --global user.name "Payroll System Developer"
    git config --global user.email "developer@payroll-system.local"
    Write-Host "Git user configured" -ForegroundColor Green
}

# Function to show Git status
function Show-GitStatus {
    Write-Host "=== Git Repository Status ===" -ForegroundColor Cyan
    git status
}

# Function to show recent commits
function Show-GitLog {
    Write-Host "=== Recent Commits ===" -ForegroundColor Cyan
    git log --oneline -10
}

# Function to add and commit changes
function Commit-Changes {
    param(
        [string]$Message = "Update payroll system"
    )
    
    Write-Host "Adding all changes..." -ForegroundColor Yellow
    git add .
    
    Write-Host "Committing changes with message: $Message" -ForegroundColor Yellow
    git commit -m $Message
    
    Write-Host "Changes committed successfully!" -ForegroundColor Green
}

# Function to create a new branch
function New-GitBranch {
    param(
        [string]$BranchName
    )
    
    Write-Host "Creating new branch: $BranchName" -ForegroundColor Yellow
    git checkout -b $BranchName
    Write-Host "Switched to branch: $BranchName" -ForegroundColor Green
}

# Function to switch branches
function Switch-GitBranch {
    param(
        [string]$BranchName
    )
    
    Write-Host "Switching to branch: $BranchName" -ForegroundColor Yellow
    git checkout $BranchName
    Write-Host "Now on branch: $BranchName" -ForegroundColor Green
}

# Function to show all branches
function Show-GitBranches {
    Write-Host "=== Available Branches ===" -ForegroundColor Cyan
    git branch -a
}

# Main menu
function Show-GitMenu {
    Write-Host "`n=== Payroll System Git Management ===" -ForegroundColor Magenta
    Write-Host "1. Show Git Status" -ForegroundColor White
    Write-Host "2. Show Recent Commits" -ForegroundColor White
    Write-Host "3. Add and Commit Changes" -ForegroundColor White
    Write-Host "4. Create New Branch" -ForegroundColor White
    Write-Host "5. Switch Branch" -ForegroundColor White
    Write-Host "6. Show All Branches" -ForegroundColor White
    Write-Host "7. Exit" -ForegroundColor White
    Write-Host "`nSelect an option (1-7): " -NoNewline
}

# Interactive menu
function Start-GitMenu {
    do {
        Show-GitMenu
        $choice = Read-Host
        
        switch ($choice) {
            "1" { Show-GitStatus }
            "2" { Show-GitLog }
            "3" { 
                $message = Read-Host "Enter commit message (or press Enter for default)"
                if ($message) {
                    Commit-Changes -Message $message
                } else {
                    Commit-Changes
                }
            }
            "4" { 
                $branchName = Read-Host "Enter new branch name"
                if ($branchName) {
                    New-GitBranch -BranchName $branchName
                }
            }
            "5" { 
                $branchName = Read-Host "Enter branch name to switch to"
                if ($branchName) {
                    Switch-GitBranch -BranchName $branchName
                }
            }
            "6" { Show-GitBranches }
            "7" { 
                Write-Host "Exiting Git menu..." -ForegroundColor Green
                break
            }
            default { Write-Host "Invalid option. Please try again." -ForegroundColor Red }
        }
        
        if ($choice -ne "7") {
            Write-Host "`nPress any key to continue..." -NoNewline
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    } while ($choice -ne "7")
}

# Auto-run if script is executed directly
if ($MyInvocation.InvocationName -eq $MyInvocation.MyCommand.Name) {
    Write-Host "Git Setup for Payroll Management System" -ForegroundColor Green
    Write-Host "Repository initialized and ready for use!" -ForegroundColor Green
    Write-Host "`nAvailable functions:" -ForegroundColor Cyan
    Write-Host "- Show-GitStatus" -ForegroundColor White
    Write-Host "- Show-GitLog" -ForegroundColor White
    Write-Host "- Commit-Changes" -ForegroundColor White
    Write-Host "- New-GitBranch" -ForegroundColor White
    Write-Host "- Switch-GitBranch" -ForegroundColor White
    Write-Host "- Show-GitBranches" -ForegroundColor White
    Write-Host "- Start-GitMenu" -ForegroundColor White
    
    Write-Host "`nRun 'Start-GitMenu' to open the interactive menu" -ForegroundColor Yellow
} 