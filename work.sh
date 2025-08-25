#!/bin/bash

get_current_version() {
    local latest_tag=$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n1 || echo "v0.0.0")
    echo "$latest_tag"
}

# Function to increment version
increment_version() {
    local current_version=${1#v}
    local increment_type=$2

    IFS='.' read -r -a version_array <<<"$current_version"
    local major=${version_array[0]:-0}
    local minor=${version_array[1]:-0}
    local patch=${version_array[2]:-0}

    case "$increment_type" in
    "major") echo "v$((major + 1)).0.0" ;;
    "minor") echo "v${major}.$((minor + 1)).0" ;;
    "patch") echo "v${major}.${minor}.$((patch + 1))" ;;
    esac
}

# Function to create a release
create_release() {
    local increment_type=$1
    local message=$2

    # Check if on main branch
    if [ "$(git branch --show-current)" != "main" ]; then
        echo "Error: Must be on main branch for releases"
        exit 1
    fi

    # Get versions
    local current_version=$(get_current_version)
    local new_version=""

    # Determine new version
    if [[ $increment_type =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        new_version=$increment_type
    else
        case "$increment_type" in
        "major" | "minor" | "patch")
            new_version=$(increment_version "$current_version" "$increment_type")
            ;;
        *)
            echo "Error: Version must be 'major', 'minor', 'patch' or specific version (e.g., v1.2.3)"
            exit 1
            ;;
        esac
    fi

    echo "Creating release $new_version (previous was $current_version)..."
    echo "Message: $message"

    # Pull latest changes
    git pull origin main

    # Add all changes for release
    git add .
    git commit -m "chore: bump version to $new_version"
    git push origin main

    # Create and push tag
    git tag -a "$new_version" -m "Release $new_version: $message"
    git push origin "$new_version"

    echo "✓ Release $new_version created"
}

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "Error: Not in a git repository"
        exit 1
    fi
}

# Function to clean up branches
cleanup_branches() {
    echo "Cleaning up merged branches..."

    # Switch to main branch
    git checkout main
    git pull origin main

    # Delete local branches that have been merged into main
    git branch --merged main | grep -v '^\*\|main\|master\|dev' | xargs -r git branch -d

    # Delete remote branches that have been merged
    git remote prune origin

    echo "✓ Branches cleaned up"
}

# Creates a new branch and pushes it to remote
create_task_branch() {
    local branch_name=$1

    # Check if we're on main branch
    if [ "$(git branch --show-current)" != "main" ]; then
        echo "Error: Must be on main branch to start a new task"
        exit 1
    fi

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- || [ -n "$(git ls-files --others --exclude-standard)" ]; then
        echo "Error: You have uncommitted changes in main branch"
        echo "Please commit or stash your changes before starting a new task"
        echo "Tip: Use 'w update' to quickly commit changes to main"
        exit 1
    fi

    # Pull latest changes
    git pull origin main

    # Create and checkout new branch
    git checkout -b "$branch_name"

    # Push to remote and set upstream
    git push -u origin "$branch_name"

    echo "✓ Created and switched to branch: $branch_name"
}

# Finishes a task by merging it into main
finish_task() {
    local message=$1
    local current_branch=$(git branch --show-current)

    # Don't allow finishing from main
    if [ "$current_branch" = "main" ]; then
        echo "Error: Already on main branch"
        exit 1
    fi

    # Check if there are any changes to commit
    if ! git diff-index --quiet HEAD -- || [ -n "$(git ls-files --others --exclude-standard)" ]; then
        echo "Committing pending changes..."
        git add .
        git commit -m "$message"
    fi

    # Push current branch
    git push origin "$current_branch"

    # Switch to main and pull
    git checkout main
    git pull origin main

    # Merge the task branch
    git merge "$current_branch" --no-ff -m "$message"

    # Push main
    git push origin main

    # Delete the task branch
    git branch -d "$current_branch"
    git push origin --delete "$current_branch"

    echo "✓ Task completed and merged to main"
}

# Function to abandon current task
abandon_task() {
    local new_branch=$1
    local current_branch=$(git branch --show-current)

    # Don't allow abandoning main
    if [ "$current_branch" = "main" ]; then
        echo "Error: Already on main branch"
        exit 1
    fi

    # First, stash any changes to avoid losing work (optional)
    # git stash save "Abandoned changes from $current_branch"

    # Switch to main and force reset working directory
    echo "Switching to main branch and resetting changes..."
    git checkout main
    git pull origin main

    # Reset any modified files to match main branch
    git reset --hard origin/main

    # Clean untracked files and directories
    git clean -fd

    # Delete the old branch
    echo "Deleting branch $current_branch..."
    git branch -D "$current_branch"
    git push origin --delete "$current_branch" 2>/dev/null || true

    # If a new branch name was provided, create it
    if [ -n "$new_branch" ]; then
        create_task_branch "$new_branch"
    fi

    echo "✓ Task abandoned and working directory reset to main"
}

# Add this new function after your other function definitions
update_main() {
    # Check if we're on main branch
    if [ "$(git branch --show-current)" != "main" ]; then
        echo "Error: Must be on main branch to update"
        exit 1
    fi

    # Add all changes
    git add .

    # Commit with message
    git commit -m "update main"

    # Push to origin
    git push origin main

    echo "✓ Main branch updated and pushed"
}

# Add this new function
finish_task_force() {
    local message=$1
    local current_branch=$(git branch --show-current)

    # Don't allow finishing from main
    if [ "$current_branch" = "main" ]; then
        echo "Error: Already on main branch"
        exit 1
    fi

    # Check if there are any changes to commit
    if ! git diff-index --quiet HEAD -- || [ -n "$(git ls-files --others --exclude-standard)" ]; then
        echo "Committing pending changes..."
        git add .
        git commit -m "$message"
    fi

    # Force push current branch
    git push -f origin "$current_branch"

    # Switch to main and pull
    git checkout main
    git pull origin main

    # Force merge the task branch
    git merge -X theirs "$current_branch" --no-ff -m "$message"

    # Force push main
    git push -f origin main

    # Delete the task branch
    git branch -D "$current_branch"
    git push origin --delete "$current_branch"

    echo "✓ Task completed and force merged to main"
}

# Function to list all open PRs
list_prs() {
    echo "Fetching open Pull Requests..."
    gh pr list --state open
}

# Function to checkout a PR branch for local testing
checkout_pr() {
    local pr_number=$1

    if [ -z "$pr_number" ]; then
        echo "Usage: w pr-checkout <pr-number>"
        echo "Available PRs:"
        list_prs
        exit 1
    fi

    echo "Checking out PR #$pr_number for local testing..."

    # Fetch the PR branch
    gh pr checkout "$pr_number"

    echo "✓ Checked out PR #$pr_number"
    echo "You can now test the changes locally"
    echo "Use 'w pr-test' to run tests on this PR"
    echo "Use 'w pr-back' to return to main branch"
}

# Function to test the current PR branch
test_pr() {
    local current_branch=$(git branch --show-current)

    if [ "$current_branch" = "main" ]; then
        echo "Error: You're on main branch. Use 'w pr-checkout <pr-number>' first"
        exit 1
    fi

    echo "Testing PR branch: $current_branch"
    echo "Running parser tests on current branch..."

    # Run our test suite
    test_all
}

# Function to run tests on PR branch
test_pr_unit() {
    local current_branch=$(git branch --show-current)

    if [ "$current_branch" = "main" ]; then
        echo "Error: You're on main branch. Use 'w pr-checkout <pr-number>' first"
        exit 1
    fi

    echo "Running parser validation on PR branch: $current_branch"

    # Run validation
    validate_setup
}

# Function to return to main branch after PR testing
return_to_main() {
    local current_branch=$(git branch --show-current)

    if [ "$current_branch" = "main" ]; then
        echo "Already on main branch"
        exit 0
    fi

    echo "Returning to main branch from PR testing..."

    # Switch to main and pull latest
    git checkout main
    git pull origin main

    # Clean up the PR branch locally (optional)
    read -p "Delete local PR branch '$current_branch'? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git branch -D "$current_branch"
        echo "✓ Deleted local PR branch: $current_branch"
    fi

    echo "✓ Back on main branch"
}

# Function to approve and merge a PR
merge_pr() {
    local pr_number=$1
    local merge_method=${2:-"squash"}

    if [ -z "$pr_number" ]; then
        echo "Usage: w pr-merge <pr-number> [merge-method]"
        echo "Merge methods: merge, squash (default), rebase"
        echo "Available PRs:"
        list_prs
        exit 1
    fi

    echo "Merging PR #$pr_number using $merge_method method..."

    # First, make sure we're on main
    git checkout main
    git pull origin main

    # Merge the PR
    case "$merge_method" in
    "merge")
        gh pr merge "$pr_number" --merge
        ;;
    "rebase")
        gh pr merge "$pr_number" --rebase
        ;;
    "squash"|*)
        gh pr merge "$pr_number" --squash
        ;;
    esac

    echo "✓ PR #$pr_number merged successfully"
    echo "Pulling latest changes to main..."
    git pull origin main
}

# Function to view PR details
view_pr() {
    local pr_number=$1

    if [ -z "$pr_number" ]; then
        echo "Usage: w pr-view <pr-number>"
        echo "Available PRs:"
        list_prs
        exit 1
    fi

    echo "Viewing PR #$pr_number details..."
    gh pr view "$pr_number"
}

# Function to list all issues
list_issues() {
    echo "Fetching GitHub Issues..."
    gh issue list --state open
}

# Function to create a new issue
create_issue() {
    local title="$1"
    local body="$2"
    local labels="$3"

    if [ -z "$title" ]; then
        echo "Usage: w issue-create \"Title\" [\"Description\"] [\"label1,label2\"]"
        echo "Example: w issue-create \"Fix login bug\" \"Users can't login with email\" \"bug,urgent\""
        exit 1
    fi

    local cmd="gh issue create --title \"$title\""

    if [ -n "$body" ]; then
        cmd="$cmd --body \"$body\""
    fi

    if [ -n "$labels" ]; then
        cmd="$cmd --label \"$labels\""
    fi

    echo "Creating issue: $title"
    eval $cmd
}

# Function to view issue details
view_issue() {
    local issue_number=$1

    if [ -z "$issue_number" ]; then
        echo "Usage: w issue-view <issue-number>"
        echo "Available issues:"
        list_issues
        exit 1
    fi

    echo "Viewing issue #$issue_number details..."
    gh issue view "$issue_number"
}

# Function to close an issue
close_issue() {
    local issue_number=$1
    local comment="$2"

    if [ -z "$issue_number" ]; then
        echo "Usage: w issue-close <issue-number> [\"closing comment\"]"
        echo "Available issues:"
        list_issues
        exit 1
    fi

    local cmd="gh issue close \"$issue_number\""

    if [ -n "$comment" ]; then
        cmd="$cmd --comment \"$comment\""
    fi

    echo "Closing issue #$issue_number..."
    eval $cmd
}

# Function to list available labels
list_labels() {
    echo "Available labels in this repository:"
    gh label list
}

# Function to list projects
list_projects() {
    echo "Available projects in this repository:"
    gh project list --owner kosirm
}

# Function to list milestones
list_milestones() {
    echo "Available milestones in this repository:"
    gh api repos/:owner/:repo/milestones --jq '.[] | "\(.number): \(.title) (\(.state)) - \(.description // "No description")"'
}

# Function to create a milestone
create_milestone() {
    local title="$1"
    local description="$2"
    local due_date="$3"

    if [ -z "$title" ]; then
        echo "Usage: w milestone-create \"Title\" [\"Description\"] [\"YYYY-MM-DD\"]"
        echo "Example: w milestone-create \"v1.0 Release\" \"First major release\" \"2024-12-31\""
        exit 1
    fi

    local cmd="gh api repos/:owner/:repo/milestones -f title=\"$title\""

    if [ -n "$description" ]; then
        cmd="$cmd -f description=\"$description\""
    fi

    if [ -n "$due_date" ]; then
        cmd="$cmd -f due_on=\"${due_date}T23:59:59Z\""
    fi

    echo "Creating milestone: $title"
    eval $cmd
}

# Enhanced function to create issue with full GitHub features
create_issue_full() {
    local title="$1"
    local body="$2"
    local labels="$3"
    local milestone="$4"
    local assignee="$5"

    if [ -z "$title" ]; then
        echo "Usage: w issue-full \"Title\" [\"Description\"] [\"label1,label2\"] [milestone-number] [assignee]"
        echo ""
        echo "Available labels:"
        gh label list --limit 20 | head -10
        echo ""
        echo "Available milestones:"
        list_milestones
        echo ""
        echo "Example: w issue-full \"Fix login\" \"Users can't login\" \"bug,urgent\" 1 \"kosirm\""
        exit 1
    fi

    local cmd="gh issue create --title \"$title\""

    if [ -n "$body" ]; then
        cmd="$cmd --body \"$body\""
    fi

    if [ -n "$labels" ]; then
        cmd="$cmd --label \"$labels\""
    fi

    if [ -n "$milestone" ]; then
        cmd="$cmd --milestone \"$milestone\""
    fi

    if [ -n "$assignee" ]; then
        cmd="$cmd --assignee \"$assignee\""
    fi

    echo "Creating issue with full options: $title"
    eval $cmd
}

# Function to test parsing a specific PDF file
test_parse() {
    local pdf_file=$1
    local output_file=$2

    if [ -z "$pdf_file" ]; then
        echo "Usage: w parse <pdf-file> [output-file]"
        echo "Example: w parse \"abby/source/pjesmarica - 0024.pdf\""
        echo "Example: w parse \"abby/source/pjesmarica - 0024.pdf\" \"test_output.html\""
        exit 1
    fi

    # Change to the parser directory
    cd "$(dirname "$0")"
    cd parser
    echo "Running in $(pwd)"

    if [ -z "$output_file" ]; then
        # Generate default output filename
        local base_name=$(basename "$pdf_file" .pdf)
        output_file="../abby/html/test_${base_name}.html"
    fi

    echo "Parsing: $pdf_file"
    echo "Output: $output_file"

    python abby_html_generator.py "../$pdf_file" -o "../$output_file"

    if [ $? -eq 0 ]; then
        echo "✓ Parsing completed successfully"
        echo "Output saved to: $output_file"
    else
        echo "❌ Parsing failed"
        exit 1
    fi
}

# Function to run all test files to check for regressions
test_all() {
    echo "Running regression tests on all known files..."

    # Change to the parser directory
    cd "$(dirname "$0")"
    cd parser
    echo "Running in $(pwd)"

    local test_files=(
        "abby/source/pjesmarica - 0024.pdf"  # Single song
        "abby/source/pjesmarica - 0026.pdf"  # Two songs side-by-side
        "abby/source/pjesmarica - 0028.pdf"  # Two songs vertical
        "abby/source/pjesmarica - 0088.pdf"  # Two songs vertical with complex roles
    )

    local failed_tests=0
    local total_tests=${#test_files[@]}

    echo "Testing $total_tests files..."
    echo ""

    for pdf_file in "${test_files[@]}"; do
        local base_name=$(basename "$pdf_file" .pdf)
        local output_file="../abby/html/regression_test_${base_name}.html"

        echo "Testing: $pdf_file"

        if python abby_html_generator.py "../$pdf_file" -o "$output_file" >/dev/null 2>&1; then
            echo "✓ PASS: $base_name"
        else
            echo "❌ FAIL: $base_name"
            ((failed_tests++))
        fi
    done

    echo ""
    echo "Test Results: $((total_tests - failed_tests))/$total_tests passed"

    if [ $failed_tests -eq 0 ]; then
        echo "✓ All regression tests passed!"
        return 0
    else
        echo "❌ $failed_tests test(s) failed"
        return 1
    fi
}

# Function to validate parser setup
validate_setup() {
    echo "Validating songbook parser setup..."

    # Change to the parser directory
    cd "$(dirname "$0")"
    cd parser
    echo "Running in $(pwd)"

    local errors=0

    # Check if required Python files exist
    local required_files=(
        "abby_html_generator.py"
        "abby_layout_detector.py"
        "abby_pdf_parser.py"
        "abby_two_songs_parser.py"
        "abby_two_songs_vertical_parser.py"
    )

    echo "Checking required parser files..."
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            echo "✓ Found: $file"
        else
            echo "❌ Missing: $file"
            ((errors++))
        fi
    done

    # Check if source directory exists
    if [ -d "../abby/source" ]; then
        echo "✓ Found: abby/source directory"
        local pdf_count=$(find "../abby/source" -name "*.pdf" | wc -l)
        echo "  Contains $pdf_count PDF files"
    else
        echo "❌ Missing: abby/source directory"
        ((errors++))
    fi

    # Check if output directory exists, create if not
    if [ -d "../abby/html" ]; then
        echo "✓ Found: abby/html directory"
    else
        echo "⚠️  Creating: abby/html directory"
        mkdir -p "../abby/html"
    fi

    # Try to import required Python modules
    echo "Checking Python dependencies..."
    if python -c "import fitz" 2>/dev/null; then
        echo "✓ PyMuPDF (fitz) is available"
    else
        echo "❌ PyMuPDF (fitz) is not installed"
        echo "   Install with: pip install PyMuPDF"
        ((errors++))
    fi

    echo ""
    if [ $errors -eq 0 ]; then
        echo "✓ Setup validation passed!"
        return 0
    else
        echo "❌ Setup validation failed with $errors error(s)"
        return 1
    fi
}

# Main script
check_git_repo

case "$1" in
"start")
    if [ -z "$2" ]; then
        echo "Usage: $0 start <branch-name>"
        exit 1
    fi
    create_task_branch "$2"
    ;;
"finish")
    if [ -z "$2" ]; then
        echo "Usage: $0 finish \"commit message\""
        exit 1
    fi
    finish_task "$2"
    ;;
"finish-force")
    if [ -z "$2" ]; then
        echo "Usage: $0 finish-force \"commit message\""
        exit 1
    fi
    finish_task_force "$2"
    ;;
"abandon")
    if [ -z "$2" ]; then
        abandon_task
    else
        abandon_task "$2"
    fi
    ;;
"cleanup")
    cleanup_branches
    ;;
"release")
    if [ -z "$2" ] || [ -z "$3" ]; then
        echo "Usage: w release <type> \"release message\""
        echo "Types:"
        echo "  major  - Breaking changes (x.0.0)"
        echo "  minor  - New features (0.x.0)"
        echo "  patch  - Bug fixes (0.0.x)"
        echo "  v1.2.3 - Specific version"
        echo ""
        echo "Examples:"
        echo "  w release patch \"Bug fixes\""
        echo "  w release minor \"New features added\""
        echo "  w release major \"Breaking changes\""
        echo "  w release v1.2.3 \"Custom version\""
        exit 1
    fi
    create_release "$2" "$3"
    ;;
# Songbook Processing Commands
"chordprofile")
    if [ -z "$2" ]; then
        echo "Usage: w chordprofile <pdf-file> [output-folder] [parser-file]"
        echo "Example: w chordprofile \"source/2-03-blag.pdf\""
        echo "Example: w chordprofile \"source/2-03-blag.pdf\" \"output\""
        echo "Example: w chordprofile \"lang/hr/03_pdf/2-03-blag.pdf\" \"lang/hr/04_chordpro\" \"lang/hr/01_src/parser/pymupdf_span_parser.py\""
        exit 1
    fi

    if [ -z "$3" ]; then
        output_dir=$(dirname "$2")
    else
        output_dir="$3"
        mkdir -p "$output_dir"
    fi

    # Determine parser file
    if [ -z "$4" ]; then
        parser_file="new_parser/phase3_acrobat_pro/parser/pymupdf_span_parser.py"
        parser_dir="new_parser/phase3_acrobat_pro/parser"
    else
        parser_file="$4"
        parser_dir=$(dirname "$parser_file")
    fi

    filename=$(basename "$2" .pdf)
    echo "🎵 Converting $filename.pdf to ChordPro format using $(basename "$parser_file")..."
    echo "   Parser: $parser_file"

    # Store absolute paths before changing directory
    input_abs_path=$(realpath "$2")
    output_abs_path=$(realpath "$output_dir")

    cd "$parser_dir"
    python $(basename "$parser_file") --input "$input_abs_path" --output "$output_abs_path/${filename}.chordpro" --song-name "$filename"

    if [ $? -eq 0 ]; then
        echo "✅ ChordPro saved to: $output_dir/${filename}.chordpro"
    else
        echo "❌ ChordPro conversion failed"
        exit 1
    fi
    ;;

"chordprofolder")
    if [ -z "$2" ]; then
        echo "Usage: w chordprofolder <pdf-folder> [output-folder] [parser-file]"
        echo "Example: w chordprofolder \"source\""
        echo "Example: w chordprofolder \"source\" \"output\""
        echo "Example: w chordprofolder \"lang/hr/03_pdf\" \"lang/hr/04_chordpro\" \"lang/hr/01_src/parser/pymupdf_span_parser.py\""
        exit 1
    fi

    if [ -z "$3" ]; then
        output_dir="$2"
    else
        output_dir="$3"
        mkdir -p "$output_dir"
    fi

    # Determine parser file
    if [ -z "$4" ]; then
        parser_file="new_parser/phase3_acrobat_pro/parser/pymupdf_span_parser.py"
        parser_dir="new_parser/phase3_acrobat_pro/parser"
    else
        parser_file="$4"
        parser_dir=$(dirname "$parser_file")
    fi

    # Create log file with timestamp
    log_file="../../../batch_processing_$(date +%Y%m%d_%H%M%S).log"

    echo "🎵 Converting PDF folder to ChordPro format using $(basename "$parser_file")..."
    echo "Source: $2"
    echo "Output: $output_dir"
    echo "Parser: $parser_file"
    echo "📝 Log file: $log_file"

    # Store absolute paths before changing directory
    source_abs_path=$(realpath "$2")
    output_abs_path=$(realpath "$output_dir")

    cd "$parser_dir"

    processed=0
    failed=0

    # Start logging
    {
        echo "=== BATCH PROCESSING LOG ==="
        echo "Started: $(date)"
        echo "Source: $2"
        echo "Output: $output_dir"
        echo "=========================="
        echo ""

        for pdf_file in "$source_abs_path"/*.pdf; do
            if [ -f "$pdf_file" ]; then
                filename=$(basename "$pdf_file" .pdf)
                echo "🎵 Processing: $filename.pdf"

                # Count ChordPro files before parsing
                files_before=$(find "$output_abs_path" -name "*.chordpro" 2>/dev/null | wc -l)

                # Let parser generate its own filename (title-based for Slovenian/Croatian)
                # Pass output directory so parser knows where to save files
                if python $(basename "$parser_file") --input "$pdf_file" --output "$output_abs_path/dummy.chordpro" --song-name "$filename" 2>&1; then
                    # Count ChordPro files after parsing
                    files_after=$(find "$output_abs_path" -name "*.chordpro" 2>/dev/null | wc -l)

                    # Check if a new file was created
                    if [ "$files_after" -gt "$files_before" ]; then
                        echo "✅ Created: title-based filename"
                        ((processed++))
                    else
                        echo "❌ Output file not created: $filename"
                        ((failed++))
                    fi
            else
                echo "❌ Failed: $filename.pdf"
                ((failed++))
            fi
        fi
        done

        echo ""
        echo "=========================="
        echo "✅ ChordPro batch processing complete:"
        echo "   📊 Processed: $processed files"
        echo "   ❌ Failed: $failed files"
        echo "   📁 Output folder: $output_dir"
        echo "Finished: $(date)"
        echo "=========================="

    } > "$log_file" 2>&1

    # Also display summary to console
    echo "✅ ChordPro batch processing complete:"
    echo "   📊 Processed: $processed files"
    echo "   ❌ Failed: $failed files"
    echo "   📁 Output folder: $output_dir"
    echo "📝 Full log saved to: $log_file"
    ;;

"htmlfile")
    if [ -z "$2" ]; then
        echo "Usage: w htmlfile <pdf-file> [output-folder] [parser-file] [html-generator-file]"
        echo "Example: w htmlfile \"source/2-03-blag.pdf\""
        echo "Example: w htmlfile \"source/2-03-blag.pdf\" \"output\""
        echo "Example: w htmlfile \"lang/hr/03_pdf/2-03-blag.pdf\" \"lang/hr/05_html\" \"lang/hr/01_src/parser/pymupdf_span_parser.py\" \"lang/hr/01_src/parser/chordpro_to_html_arial.py\""
        exit 1
    fi

    if [ -z "$3" ]; then
        output_dir=$(dirname "$2")
    else
        output_dir="$3"
        mkdir -p "$output_dir"
    fi

    # Determine parser file
    if [ -z "$4" ]; then
        parser_file="new_parser/phase3_acrobat_pro/parser/pymupdf_span_parser.py"
        parser_dir="new_parser/phase3_acrobat_pro/parser"
    else
        parser_file="$4"
        parser_dir=$(dirname "$parser_file")
    fi

    # Determine HTML generator file
    if [ -z "$5" ]; then
        html_generator_file="new_parser/phase3_acrobat_pro/parser/chordpro_to_html_arial.py"
        html_generator_dir="new_parser/phase3_acrobat_pro/parser"
    else
        html_generator_file="$5"
        html_generator_dir=$(dirname "$html_generator_file")
    fi

    filename=$(basename "$2" .pdf)
    echo "🌐 Converting $filename.pdf to HTML format..."
    echo "   Parser: $(basename "$parser_file")"
    echo "   HTML Generator: $(basename "$html_generator_file")"

    # Store absolute paths before changing directory
    input_abs_path=$(realpath "$2")
    output_abs_path=$(realpath "$output_dir")
    html_generator_abs_dir=$(realpath "$html_generator_dir")

    # First generate ChordPro
    echo "  Step 1: Generating ChordPro..."
    cd "$parser_dir"
    if python $(basename "$parser_file") --input "$input_abs_path" --output "/tmp/${filename}.chordpro" --song-name "$filename"; then
        # Then convert to HTML
        echo "  Step 2: Converting to HTML..."
        cd "$html_generator_abs_dir"
        if python $(basename "$html_generator_file") --input "/tmp/${filename}.chordpro" --output "$output_abs_path/${filename}.html"; then
            rm "/tmp/${filename}.chordpro"  # Clean up temp file
            echo "✅ HTML saved to: $output_dir/${filename}.html"
        else
            echo "❌ HTML conversion failed"
            rm "/tmp/${filename}.chordpro"  # Clean up temp file
            exit 1
        fi
    else
        echo "❌ ChordPro generation failed"
        exit 1
    fi
    ;;

"htmlfolder")
    if [ -z "$2" ]; then
        echo "Usage: w htmlfolder <chordpro-folder> [output-folder] [html-generator-file]"
        echo "Example: w htmlfolder \"new_parser/chordpro_output\""
        echo "Example: w htmlfolder \"new_parser/chordpro_output\" \"new_parser/html_output\""
        echo "Example: w htmlfolder \"lang/hr/04_chordpro\" \"lang/hr/05_html\" \"lang/hr/01_src/parser/chordpro_to_html_arial.py\""
        exit 1
    fi

    if [ -z "$3" ]; then
        output_dir="$2"
    else
        output_dir="$3"
        mkdir -p "$output_dir"
    fi

    # Determine HTML generator file
    if [ -z "$4" ]; then
        html_generator_file="new_parser/phase3_acrobat_pro/parser/chordpro_to_html_arial.py"
        html_generator_dir="new_parser/phase3_acrobat_pro/parser"
    else
        html_generator_file="$4"
        html_generator_dir=$(dirname "$html_generator_file")
    fi

    echo "🌐 Converting ChordPro folder to HTML format..."
    echo "Source: $2"
    echo "Output: $output_dir"
    echo "HTML Generator: $(basename "$html_generator_file")"

    # Store absolute paths before changing directory
    source_abs_path=$(realpath "$2")
    output_abs_path=$(realpath "$output_dir")

    cd "$html_generator_dir"

    processed=0
    failed=0

    for chordpro_file in "$source_abs_path"/*.chordpro; do
        if [ -f "$chordpro_file" ]; then
            filename=$(basename "$chordpro_file" .chordpro)
            echo "🌐 Processing: $filename.chordpro"

            # Convert ChordPro to HTML
            if python $(basename "$html_generator_file") --input "$chordpro_file" --output "$output_abs_path/${filename}.html"; then
                ((processed++))
            else
                echo "❌ HTML conversion failed: $filename.chordpro"
                ((failed++))
            fi
        fi
    done

    echo "✅ HTML batch processing complete:"
    echo "   📊 Processed: $processed files"
    echo "   ❌ Failed: $failed files"
    echo "   📁 Output folder: $output_dir"
    ;;

"htmlfile-equal")
    if [ -z "$2" ]; then
        echo "Usage: w htmlfile-equal <chordpro-file> [output-folder] [html-generator-file]"
        echo "Example: w htmlfile-equal \"new_parser/title_based_output/2-03-BLAG.chordpro\""
        echo "Example: w htmlfile-equal \"new_parser/title_based_output/2-03-BLAG.chordpro\" \"output\""
        echo "Example: w htmlfile-equal \"lang/hr/04_chordpro/song.chordpro\" \"lang/hr/05_html\" \"lang/hr/01_src/parser/chordpro_to_html_equal_spacing.py\""
        exit 1
    fi

    if [ -z "$3" ]; then
        output_dir=$(dirname "$2")
    else
        output_dir="$3"
        mkdir -p "$output_dir"
    fi

    # Determine HTML generator file
    if [ -z "$4" ]; then
        html_generator_file="new_parser/phase3_acrobat_pro/parser/chordpro_to_html_equal_spacing.py"
        html_generator_dir="new_parser/phase3_acrobat_pro/parser"
    else
        html_generator_file="$4"
        html_generator_dir=$(dirname "$html_generator_file")
    fi

    filename=$(basename "$2" .chordpro)
    echo "🌐 Converting $filename.chordpro to HTML format (Equal Spacing)..."
    echo "   HTML Generator: $(basename "$html_generator_file")"

    # Store absolute paths before changing directory
    input_abs_path=$(realpath "$2")
    output_abs_path=$(realpath "$output_dir")

    cd "$html_generator_dir"

    # Convert ChordPro to HTML with equal spacing
    html_filename="${filename}.html"
    if python $(basename "$html_generator_file") --input "$input_abs_path" --output "$output_abs_path/$html_filename"; then
        echo "✅ HTML (Equal Spacing) conversion complete: $html_filename"
    else
        echo "❌ HTML conversion failed"
        exit 1
    fi
    ;;

"htmlfolder-equal")
    if [ -z "$2" ]; then
        echo "Usage: w htmlfolder-equal <chordpro-folder> [output-folder] [html-generator-file]"
        echo "Example: w htmlfolder-equal \"new_parser/chordpro_output\""
        echo "Example: w htmlfolder-equal \"new_parser/chordpro_output\" \"new_parser/html_output\""
        echo "Example: w htmlfolder-equal \"lang/hr/04_chordpro\" \"lang/hr/05_html\" \"lang/hr/01_src/parser/chordpro_to_html_equal_spacing.py\""
        exit 1
    fi

    if [ -z "$3" ]; then
        output_dir="$2"
    else
        output_dir="$3"
        mkdir -p "$output_dir"
    fi

    # Determine HTML generator file
    if [ -z "$4" ]; then
        html_generator_file="new_parser/phase3_acrobat_pro/parser/chordpro_to_html_equal_spacing.py"
        html_generator_dir="new_parser/phase3_acrobat_pro/parser"
    else
        html_generator_file="$4"
        html_generator_dir=$(dirname "$html_generator_file")
    fi

    echo "🌐 Converting ChordPro folder to HTML format (Equal Spacing)..."
    echo "Source: $2"
    echo "Output: $output_dir"
    echo "HTML Generator: $(basename "$html_generator_file")"

    # Store absolute paths before changing directory
    source_abs_path=$(realpath "$2")
    output_abs_path=$(realpath "$output_dir")

    cd "$html_generator_dir"

    processed=0
    failed=0

    for chordpro_file in "$source_abs_path"/*.chordpro; do
        if [ -f "$chordpro_file" ]; then
            filename=$(basename "$chordpro_file" .chordpro)
            echo "🌐 Processing: $filename.chordpro"

            # Convert ChordPro to HTML with equal spacing
            if python $(basename "$html_generator_file") --input "$chordpro_file" --output "$output_abs_path/${filename}.html"; then
                ((processed++))
            else
                echo "❌ HTML conversion failed: $filename.chordpro"
                ((failed++))
            fi
        fi
    done

    echo "✅ HTML (Equal Spacing) batch processing complete:"
    echo "   📊 Processed: $processed files"
    echo "   ❌ Failed: $failed files"
    echo "   📁 Output folder: $output_dir"
    ;;

"test")
    test_all
    ;;
"validate")
    validate_setup
    ;;




"update")
    update_main
    ;;


"pr-list")
    list_prs
    ;;
"pr-checkout")
    if [ -z "$2" ]; then
        echo "Usage: w pr-checkout <pr-number>"
        echo "Available PRs:"
        list_prs
        exit 1
    fi
    checkout_pr "$2"
    ;;
"pr-test")
    test_pr
    ;;
"pr-validate")
    test_pr_unit
    ;;
"pr-back")
    return_to_main
    ;;
"pr-merge")
    if [ -z "$2" ]; then
        echo "Usage: w pr-merge <pr-number> [merge-method]"
        echo "Merge methods: merge, squash (default), rebase"
        exit 1
    fi
    merge_pr "$2" "$3"
    ;;
"pr-view")
    if [ -z "$2" ]; then
        echo "Usage: w pr-view <pr-number>"
        exit 1
    fi
    view_pr "$2"
    ;;
"issue-list")
    list_issues
    ;;
"issue-create")
    if [ -z "$2" ]; then
        echo "Usage: w issue-create \"Title\" [\"Description\"] [\"label1,label2\"]"
        exit 1
    fi
    create_issue "$2" "$3" "$4"
    ;;
"issue-view")
    if [ -z "$2" ]; then
        echo "Usage: w issue-view <issue-number>"
        exit 1
    fi
    view_issue "$2"
    ;;
"issue-close")
    if [ -z "$2" ]; then
        echo "Usage: w issue-close <issue-number> [\"closing comment\"]"
        exit 1
    fi
    close_issue "$2" "$3"
    ;;
"issue-full")
    if [ -z "$2" ]; then
        echo "Usage: w issue-full \"Title\" [\"Description\"] [\"label1,label2\"] [milestone-number] [assignee]"
        exit 1
    fi
    create_issue_full "$2" "$3" "$4" "$5" "$6"
    ;;
"labels")
    list_labels
    ;;
"projects")
    list_projects
    ;;
"milestones")
    list_milestones
    ;;
"milestone-create")
    if [ -z "$2" ]; then
        echo "Usage: w milestone-create \"Title\" [\"Description\"] [\"YYYY-MM-DD\"]"
        exit 1
    fi
    create_milestone "$2" "$3" "$4"
    ;;
*)
    echo "Usage: w {start|finish|finish-force|abandon|release|update|parse|test|validate|pr-list|pr-checkout|pr-test|pr-validate|pr-back|pr-merge|pr-view|issue-list|issue-create|issue-view|issue-close|issue-full|labels|projects|milestones|milestone-create} [args]"
    echo ""
    echo "Commands:"
    echo "  start <branch-name>        - Start a new task branch"
    echo "  finish \"message\"           - Complete current task and merge to main"
    echo "  finish-force \"message\"     - Force complete task and overwrite main"
    echo "  abandon [new-branch]       - Abandon current task, optionally start new branch"
    echo "  release <type> \"msg\"       - Create a new release version"
    echo "  update                     - Quick update of main branch (must be on main)"
    echo ""
    echo "Songbook Processing Commands:"
    echo "  chordprofile <pdf> [folder] [parser]     - Convert single PDF to ChordPro format"
    echo "  chordprofolder <folder> [out] [parser]   - Convert PDF folder to ChordPro format"
    echo "  htmlfile <pdf> [folder] [parser] [html]  - Convert single PDF to HTML format"
    echo "  htmlfolder <folder> [out] [html]         - Convert ChordPro folder to HTML format"
    echo "  htmlfile-equal <chordpro> [folder] [html] - Convert single ChordPro to HTML (Equal Spacing)"
    echo "  htmlfolder-equal <folder> [out] [html]   - Convert ChordPro folder to HTML (Equal Spacing)"
    echo "  test                         - Run regression tests on all known files"
    echo "  validate                     - Validate parser setup and dependencies"
    echo ""
    echo "Pull Request Commands (requires GitHub CLI):"
    echo "  pr-list                   - List all open Pull Requests"
    echo "  pr-checkout <pr-number>   - Checkout a PR branch for local testing"
    echo "  pr-test                   - Run parser tests on current PR branch"
    echo "  pr-validate               - Run parser validation on current PR branch"
    echo "  pr-back                   - Return to main branch after PR testing"
    echo "  pr-merge <pr-number>      - Approve and merge a PR (default: squash)"
    echo "  pr-view <pr-number>       - View detailed information about a PR"
    echo ""
    echo "GitHub Issues Commands (requires GitHub CLI):"
    echo "  issue-list                - List all open GitHub Issues"
    echo "  issue-create \"title\"      - Create a new issue (with optional description and labels)"
    echo "  issue-full \"title\"        - Create issue with full options (labels, milestone, assignee)"
    echo "  issue-view <issue-number> - View detailed information about an issue"
    echo "  issue-close <issue-number> - Close an issue (with optional comment)"
    echo ""
    echo "GitHub Organization Commands:"
    echo "  labels                    - List all available labels"
    echo "  projects                  - List all available projects"
    echo "  milestones                - List all available milestones"
    echo "  milestone-create \"title\"  - Create a new milestone (with optional description and due date)"
    echo ""
    echo "Examples:"
    echo "  w start fix-z-role-parsing               - Start new task"
    echo "  w finish \"Fixed Z role parsing\"          - Complete task and merge to main"
    echo "  w finish-force \"Fixed Z role parsing\"    - Force complete task and overwrite main"
    echo "  w abandon                                - Just abandon current task"
    echo "  w abandon new-feature                    - Abandon and start new task \"new-feature\""
    echo "  w cleanup                                - Delete all merged branches"
    echo "  w release patch \"Bug fixes\"              - Release patch with comment \"Bug fixes\""
    echo "  w release minor \"New features\"           - Release minor with comment \"New features\""
    echo "  w release major \"Breaking changes\"       - Release major with comment \"Breaking changes\""
    echo "  w update                                 - Quick update of main branch"
    echo "  w chordprofile \"source/2-03-blag.pdf\"   - Convert single PDF to ChordPro (default parser)"
    echo "  w chordprofile \"lang/hr/03_pdf/song.pdf\" \"lang/hr/04_chordpro\" \"lang/hr/01_src/parser/pymupdf_span_parser.py\" - Language-specific conversion"
    echo "  w chordprofolder \"source\" \"output\"      - Convert all PDFs in folder to ChordPro (default parser)"
    echo "  w chordprofolder \"lang/hr/03_pdf\" \"lang/hr/04_chordpro\" \"lang/hr/01_src/parser/pymupdf_span_parser.py\" - Language-specific batch conversion"
    echo "  w htmlfile \"source/2-03-blag.pdf\"       - Convert single PDF to HTML (default generators)"
    echo "  w htmlfolder \"lang/hr/04_chordpro\" \"lang/hr/05_html\" \"lang/hr/01_src/parser/chordpro_to_html_arial.py\" - Language-specific HTML conversion"
    echo "  w htmlfile-equal \"chordpro/song.chordpro\" - Convert single ChordPro to HTML (Equal Spacing, default generator)"
    echo "  w htmlfolder-equal \"lang/hr/04_chordpro\" \"lang/hr/05_html\" \"lang/hr/01_src/parser/chordpro_to_html_equal_spacing.py\" - Language-specific equal spacing"
    echo "  w test                                   - Run regression tests on all files"
    echo "  w validate                               - Validate parser setup and dependencies"
    echo "  w pr-list                                - List all open Pull Requests"
    echo "  w pr-checkout 123                        - Checkout PR #123 for local testing"
    echo "  w pr-test                                - Run parser tests on current PR branch"
    echo "  w pr-validate                            - Run parser validation on current PR branch"
    echo "  w pr-back                                - Return to main branch after testing"
    echo "  w pr-merge 123                           - Merge PR #123 using squash method"
    echo "  w pr-merge 123 rebase                    - Merge PR #123 using rebase method"
    echo "  w pr-view 123                            - View details of PR #123"
    echo "  w issue-list                             - List all open GitHub Issues"
    echo "  w issue-create \"Fix login bug\"                            - Create a simple issue"
    echo "  w issue-create \"Feature\" \"Description\" \"enhancement\"      - Create issue with description and labels"
    echo "  w issue-full \"Fix bug\" \"Details\" \"bug\" 1 \"kosirm\"         - Create issue with milestone and assignee"
    echo "  w issue-view 456                                          - View details of issue #456"
    echo "  w issue-close 456 \"Fixed in PR #123\"                      - Close issue with comment"
    echo "  w labels                                                  - List all available labels"
    echo "  w projects                                                - List all available projects"
    echo "  w milestones                                              - List all milestones"
    echo "  w milestone-create \"v1.0\" \"Milestone 1\" \"2024-12-31\"      - Create milestone with due date"
    exit 1
    ;;
esac
