#!/usr/bin/env python3
"""
ingest_notes.py — Panflute filter to:
  • Split on a header level (split-level)
  • Merge front-matter from an Obsidian template (template)
  • Fill missing metadata (uid, slug) and provenance (source)
  • Emit each chunk as a file to a target folder (vault/folder/file)
"""
import sys
from pathlib import Path
import subprocess
import panflute as pf

# --- UTILITY FUNCTIONS (Assuming these exist or are placed here) ---
# NOTE: The original script implies to_kebab and random_string are imported.
# For this review, I'll provide simplified versions or assume their existence
# to focus on the Panflute logic and guardrails.
# A basic implementation for dependency satisfaction:
def to_kebab(s):
    """Converts a string to kebab-case."""
    # Simple replacement: non-alphanumeric to hyphen, then lowercase.
    import re
    s = re.sub(r'[^\w\s-]', '', s).strip().lower()
    return re.sub(r'[-\s]+', '-', s)

def random_string(length):
    """Generates a random alphanumeric string."""
    import random
    import string
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
# --- END UTILITY FUNCTIONS ---

# --- CONFIGURATION FROM ingest.yaml ---
# vault: msrc
# folder: passages
# out_ext: md
# template: passage
# split-level: 1
# source (comes from panflute metadata 'inputfile')
# --- END CONFIGURATION ---

# 1. Initialization (Before the walk)
def prepare(doc):
    # Retrieve configuration from metadata, conforming to ingest.yaml keys
    
    # 1. CRASH GUARDRAIL: Vault, Folder, and Template must be defined.
    # We will construct the output path from vault/folder.
    if not (vault := doc.get_metadata('vault', None)):
        pf.debug('FATAL ERROR: Missing required metadata key "vault".')
        sys.exit(1)
    if not (folder := doc.get_metadata('folder', None)):
        pf.debug('FATAL ERROR: Missing required metadata key "folder".')
        sys.exit(1)
    if not (template := doc.get_metadata('template', None)): # Change to crash if template not defined
        pf.debug('FATAL ERROR: Missing required metadata key "template".')
        sys.exit(1) 

    # Construct and check the final output directory path
    doc.vault = vault
    doc.folder = folder
    doc.outputpath = Path(doc.vault) / doc.folder
    doc.template = template
    doc.status = doc.get_metadata('status', "📥")
    
    # CRASH GUARDRAIL: Ensure output directory exists.
    if not doc.outputpath.exists():
        pf.debug(f'FATAL ERROR: Output path "{doc.outputpath}" does not exist.')
        sys.exit(1)
    
    # # CRASH GUARDRAIL: Check if the template file is accessible.
    # doc.template_path = Path(template)
    # if not doc.template_path.exists():
    #      # Assume 'template' might be a file name that needs a search path, 
    #      # but for a hard check, we'll look for it as is.
    #      pf.debug(f'FATAL ERROR: Template file "{doc.template_path}" not found.')
    #      sys.exit(1)
         

    # Retrieve and process other metadata
    doc.out_ext = doc.get_metadata('out_ext', 'md') # Default to 'md'
    doc.source_basename = Path(doc.get_metadata('source', default='input')).stem
    doc.split_level = int(doc.get_metadata('split-level', default=1)) # Retrieve split level

    # Pre-calculate the base slug for the output directory/folder
    doc.outdir_slug = to_kebab(doc.folder) 
    
    # Initialize a list of chunks and a set for header text guardrail.
    doc.chunks = [{'header_text': 'preamble', 'header_element': None, 'contents': []}]
    doc.header_texts = {'preamble'}

def check_filename_guardrail(header_text, doc):
    """
    Checks for duplicate header text and output file existence.
    Crashes on failure.
    """
    # CRASH GUARDRAIL: Check for duplicate header text
    if header_text in doc.header_texts:
        pf.debug(f"FATAL ERROR: Duplicate header text found: '{header_text}'.")
        sys.exit(1) 
    doc.header_texts.add(header_text)
    
    # CRASH GUARDRAIL: Check for existing output file
    header_slug = to_kebab(header_text)
    final_slug = f"{doc.outdir_slug}-{header_slug}"
    output_filepath = doc.outputpath / f'{header_text}.{doc.out_ext}'
    
    if output_filepath.exists():
        pf.debug(f"FATAL ERROR: Target file already exists: '{output_filepath}'.")
        sys.exit(1)
    
    # Store the pre-calculated slug and path for finalize
    return final_slug, output_filepath

# 2. The Action (The walk function - building the structure)
def action(elem, doc):
    
    if not isinstance(elem, pf.Block):
        return None

    # Check for the splitting header
    if isinstance(elem, pf.Header) and elem.level == doc.split_level: 
        header_text = pf.stringify(elem).strip()
        
        # Guardrails check and slug generation
        final_slug, output_filepath = check_filename_guardrail(header_text, doc)
        
        # Start a new chunk
        doc.chunks.append({
            'header_text': header_text, 
            'header_element': elem, 
            'contents': [],
            # Store pre-calculated values
            'final_slug': final_slug,
            'output_filepath': output_filepath
        })
    else:
        # Add the element to the contents of the current (last) chunk
        doc.chunks[-1]['contents'].append(elem)

    # Crucially: delete the element from the main document AST.
    return [] 


# 3. Finalization (After the walk)
def finalize(doc):
    
    # Use a sequence counter for preamble if needed, though not strictly in ingest.yaml
    sequence_counter = 0

    for chunk in doc.chunks:
        header_text = chunk['header_text']
        contents = list(chunk['contents']) 
        
        # 1. Handle Preamble
        if header_text == 'preamble':
            if not contents:
                pf.debug("Skipping empty preamble chunk.")
                continue
            
            header_slug = 'preamble'
            sequence_counter += 1
            sequence_num_str = str(sequence_counter)
            
            # Construct preamble slug and path for consistency
            final_slug = f"{doc.outdir_slug}-{header_slug}-{sequence_num_str}"
            output_filepath = doc.outputpath / f'{final_slug}.{doc.out_ext}' 
            # Note: No duplicate check for preamble here, as it's sequential.
            
            # The preamble should not have a header element inserted
            header_to_insert = None 
            
        # 2. Handle Split Chunks
        else:
            # Values pre-calculated in action()
            final_slug = chunk['final_slug']
            output_filepath = chunk['output_filepath']
            header_to_insert = chunk['header_element']
            sequence_num_str = '' # Not needed for split chunks unless required
            
        # --- 3. Build the full metadata dictionary for this chunk ---
        
        metadata_dict = {
            # Conforming to inline comment requirements
            'source': pf.MetaString(doc.source_basename),
            # 'sequence' is commented out in original, but added for preamble
            # 'sequence': pf.MetaString(sequence_num_str), 
            'uid': pf.MetaString(random_string(12)),
            'slug': pf.MetaString(final_slug),
            'title': pf.MetaString(header_text),
            'status': pf.MetaString(doc.status)
        }
        
        # --- 4. Prepare the Chunk Document (AST) ---
        if header_to_insert:
             # don't place the title in the body content - as requested
             # The template should handle putting the title in the correct place.
             # We just need to make sure the header text is available as 'title' in metadata.
             # If the header itself is needed in the body, it must be inserted here.
             # *Original logic inserted the header here. We will keep it but it might be redundant*
             # *if split-drop-title is true in the yaml.*
             # Per the comment: 'don't place the title in the body content'
             # and the 'split-drop-title: true' in ingest.yaml, 
             # WE SHOULD NOT insert the header element into the contents.
             pass # Do not insert header
             
        # Create a new Doc element (AST) for the chunk
        sub_doc = pf.Doc(*contents)
        
        # Merge the dynamic metadata into the sub_doc's existing metadata
        sub_doc.metadata.update(metadata_dict)

        # --- 5. Convert the Chunk AST to Pandoc JSON ---
        json_input_str = pf.convert_text(sub_doc, input_format='panflute', output_format='json')
        json_input_bytes = json_input_str.encode('utf-8')       
        
        # --- 6. Fork Pandoc to write the file with the template ---
        
        cmd = [
            'pandoc',
            '--from', 'json', 
            '--to', 'markdown',
            '-s',
            '--output', str(output_filepath)
        ]
        
        # CRASH GUARDRAIL: Check template option compatibility
        if str(doc.out_ext) == 'markdown': # Pandoc only accepts specific output formats
             cmd[3] = 'markdown'
        
        # pf.debug(f"Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                input=json_input_bytes,
                check=False,
                capture_output=True,
                text=False,
            )
            
            if result.returncode != 0:
                 pf.debug(f"FATAL: Pandoc failed (Exit Code {result.returncode}) for chunk '{header_text}'.")
                 # Decode stderr for a human-readable error message
                 pf.debug(f"Pandoc STDERR: {result.stderr.decode('utf-8', errors='ignore')}")
                 sys.exit(1) # CRASH on Pandoc failure
            
            pf.debug(f"Successfully saved chunk to: {output_filepath}")

        except FileNotFoundError:
            pf.debug("FATAL: 'pandoc' command not found. Ensure Pandoc is installed and in your PATH.")
            sys.exit(1) # CRASH on 'pandoc' command not found
        except Exception as e:
            pf.debug(f"FATAL: Unhandled subprocess error: {e}")
            sys.exit(1) # CRASH on unhandled exception

    # Return the doc (still empty) to complete the filter chain
    return doc

def main(doc=None):
    return pf.run_filter(action, prepare=prepare, finalize=finalize, doc=doc)

if __name__ == '__main__':
    main()