# Translation Team Workflow

## Overview
This document orchestrates Claude Code agents to translate business strategy Markdown files from English to Chinese with quality control.

## Agent Workflow

### 0. Chief Editor (Pre-Translation Analysis)
**Role**: Strategic analysis and briefing coordinator
**Task**: Analyze source document and create comprehensive translation briefing

**Instructions**:

1. **Document Analysis**:
   - Identify document type, purpose, and target audience
   - Note key themes, concepts, and strategic frameworks
   - Assess complexity level and specialized terminology density

2. **Translation Briefing Creation**:
   - **Background & Context**: Document purpose, business domain, and strategic importance
   - **Target Audience**: Chinese business professionals, executives, or strategists
   - **Translation Strategy**: 
     - Terminology approach (literal vs. localized business concepts)
     - Cultural adaptation requirements for Chinese business context
     - Formatting and structure preservation needs
   - **Key Challenges**: Technical terms, cultural references, or complex concepts requiring special attention
   - **Quality Standards**: Expected accuracy level and review criteria

3. **Handoff Preparation**:
   - Create glossary of critical terms with preferred Chinese translations
   - Flag sections requiring extra attention or cultural sensitivity
   - Set expectations for translation consistency across chunks

### 1. Translator Agent
**Role**: Primary translator
**Task**: Translate English business strategy content to Chinese
**Instructions**:

- Maintain Markdown formatting
- Focus on business strategy terminology accuracy
- Preserve document structure and links
- Use professional business Chinese

### 2. Editor Agent
**Role**: Quality reviewer with business strategy expertise
**Task**: Review and refine translations through 3 rounds
**Instructions**:

- Round 1: Check terminology and context accuracy
- Round 2: Improve flow and readability for Chinese audience
- Round 3: Final master-level quality review
- Use extra thinking tokens for thorough analysis

## Process Flow
1. Input: English Markdown files
2. Chunk documents for processing
3. Translator Agent processes each chunk
4. Editor Agent performs 3-round review
5. Output: High-quality Chinese Markdown files

## File Structure
```text
input/          # English markdown files
chunks/         # Processed chunks
translated/     # Initial translations
reviewed/       # Editor-reviewed content
output/         # Final Chinese files
```

## Usage

Run agents in sequence with proper handoffs between translation and editing phases.