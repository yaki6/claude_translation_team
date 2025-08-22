# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Translation team system that processes business strategy Markdown files from English to Chinese using coordinated Claude Code agents.

## Agent Workflow
1. **Chief Editor Briefing Agent**: Pre-translation analysis and briefing creation
2. **Business Strategy Translator Agent**: Translates English content to Chinese with business strategy focus
3. **Chinese Business Editor Agent**: Performs 3-round quality review with domain expertise

## Processing Flow
- Agents work through all markdown files in `data/chunks_20k/` directory sequentially
- Each chunk is processed through the complete workflow (briefing → translate → edit)
- Final output is consolidated into a single markdown file in `data/output/`

## System Requirements
- **Idempotency**: Check which chunks are completed, skip processed chunks, resume from last incomplete chunk
- **State Logging**: Use scratchpad to log translation state, progress, and completion status for each chunk

## Directory Structure
```
data/
├── chunks_20k/     # Source English markdown chunk files
├── briefings/      # Chief editor analysis outputs
├── translated/     # Translator outputs
├── reviewed/       # Editor outputs (round1/, round2/, final/)
├── state/          # Scratchpad files for progress tracking
└── output/         # Final consolidated Chinese translation
```

## Key Files
- `translation_workflow.md`: Main orchestration document for agent coordination
- `data/chunks_20k/`: Source English markdown chunk files to process
- `data/output/final_chinese_translation.md`: Final translated output

## Setup Instructions

### 1. Initialize Directory Structure
```bash
mkdir -p data/{chunks_20k,briefings,translated,reviewed/round1,reviewed/round2,reviewed/final,state,output}
```

### 2. Prepare Input Data
- Place English markdown chunk files in `data/chunks_20k/`
- Ensure files are named consistently (e.g., `chunk_001.md`, `chunk_002.md`)

### 3. Validate Setup
- Verify chunks exist: `ls data/chunks_20k/`
- Check directory structure is complete

## Usage

### Sequential Workflow
Execute agents in this order:

1. **Chief Editor Briefing**: 
   ```
   /task chief-editor-briefing "Analyze all chunks in data/chunks_20k/ and create briefings"
   ```

2. **Business Strategy Translator**:
   ```
   /task business-strategy-translator "Translate all chunks using briefings from data/briefings/"
   ```

3. **Chinese Business Editor**:
   ```
   /task chinese-business-editor "Review and refine all translations through 3 rounds"
   ```

### Resume Interrupted Workflow
Agents automatically check state files and resume from last incomplete chunk.

## Error Handling

- **Missing chunks**: Verify `data/chunks_20k/` contains markdown files
- **Interrupted workflow**: Agents resume from scratchpad state files
- **Partial failures**: Check individual chunk status in `data/state/` files