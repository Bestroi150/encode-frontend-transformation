import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict
from io import BytesIO
from PIL import Image
import requests
import plotly.express as px
import re

# Define TEI XML namespace
NS = {
    'tei': 'http://www.tei-c.org/ns/1.0',
    'xml': 'http://www.w3.org/XML/1998/namespace'
}

st.sidebar.header("Project Information")
st.sidebar.markdown("""
    **Epigraphic Database Viewer** is a tool designed to visualize and analyze ancient inscriptions.
    
    **Features**:
    This app can be used to convert TEI-encoded Telamon EpiDoc XML inscriptions into searchable visualizations with statistical information. 
    It was developed for the Front-End Data Processing and Visualization lecture (May 23, 2025) at the University of Parma, Italy, within 
    the Erasmus+ BIP Intensive ENCODE week (May 18–24, 2025).

    **Developed by**:
    Kristiyan Simeonov, Sofia University "St. Kliment Ohridski"
""")

def safe_find_text(elem, xpath, default="", lang=None):
    """
    Safely find and extract text from an XML element, providing a default if not found.
    Also handles language-specific elements.
    """
    if elem is None:
        return default
    try:
        if lang:
            xpath = f"{xpath}[@xml:lang='{lang}']"
        found = elem.find(xpath, NS)
        if found is not None and found.text:
            return found.text.strip()
        return default
    except Exception as e:
        st.warning(f"Error extracting text using xpath {xpath}: {str(e)}")
        return default

def safe_get_attr(elem, attr_name, default=""):
    """
    Safely get an attribute from an XML element, providing a default if not found.
    """
    if elem is None:
        return default
    try:
        return elem.get(attr_name, default)
    except Exception as e:
        st.warning(f"Error getting attribute {attr_name}: {str(e)}")
        return default

def validate_dimensions(dimensions_elem):
    """
    Validate and extract dimensions from a dimensions element.
    Returns a tuple of (height, width, depth) with appropriate warnings for missing values.
    """
    if dimensions_elem is None:
        return ("", "", "")
    
    height = width = depth = ""
    warnings = []
    
    try:
        height_elem = dimensions_elem.find("tei:height", NS)
        if height_elem is not None and height_elem.text:
            height = height_elem.text.strip()
        else:
            warnings.append("height")
            
        width_elem = dimensions_elem.find("tei:width", NS)
        if width_elem is not None and width_elem.text:
            width = width_elem.text.strip()
        else:
            warnings.append("width")
            
        depth_elem = dimensions_elem.find("tei:depth", NS)
        if depth_elem is not None and depth_elem.text:
            depth = depth_elem.text.strip()
        else:
            warnings.append("depth")
            
        if warnings:
            st.warning(f"Missing dimension values: {', '.join(warnings)}")
            
    except Exception as e:
        st.error(f"Error processing dimensions: {str(e)}")
        return ("", "", "")
        
    return (height, width, depth)

def get_text(elem, xpath, lang=None):
    """
    Helper function to fetch text content for a given XPath.
    Optionally filters by xml:lang attribute.
    """
    if lang:
        xpath = f"{xpath}[@xml:lang='{lang}']"
    found = elem.find(xpath, NS)
    if found is not None and found.text:
        return found.text.strip()
    return ""

def parse_tei(file):
    try:
        # Make sure we're at the start of the file
        file.seek(0)
        tree = ET.parse(file)
        root = tree.getroot()
        
        # Validate basic TEI structure
        if root.tag != "{http://www.tei-c.org/ns/1.0}TEI":
            st.warning(f"Warning: File {file.name} doesn't appear to be a valid TEI document. Root element is {root.tag}")
            return None, ""
            
        # Check for required major sections
        tei_header = root.find("tei:teiHeader", NS)
        text_elem = root.find("tei:text", NS)
        
        if tei_header is None:
            st.warning(f"Warning: File {file.name} is missing teiHeader section")
        if text_elem is None:
            st.warning(f"Warning: File {file.name} is missing text section")
            
        return root, ET.tostring(root, encoding="unicode")
    except ET.ParseError as e:
        st.error(f"XML Parsing Error in file {file.name}: {str(e)}")
        return None, ""
    except Exception as e:
        st.error(f"Error processing file {file.name}: {str(e)}")
        return None, ""

def format_leiden_text(elem):
    """
    Recursively traverse the element tree to create a plain text version of the
    Greek text (edition) with Leiden+ style formatting, covering full EpiDoc cases.
    """
    text = ''
    if elem.text:
        text += elem.text

    for child in elem:
        tag = child.tag.split('}')[-1]

        # Line break without split
        if tag == 'lb' and child.attrib.get('break') == 'no':
            pass
        # Line break
        elif tag == 'lb':
            text += '\n'

        # Text divisions
        elif tag == 'div' and child.attrib.get('type') == 'textpart':
            n = child.attrib.get('n') or ''
            inner = format_leiden_text(child)
            text += f'<D=.{n} {inner} =D>'

        # Unclear letters
        elif tag == 'unclear':
            for ch in (child.text or ''):
                text += f'{ch}\u0323'

        # Original letters
        elif tag == 'orig':
            text += f'={child.text or ""}='

        # Supplied text
        elif tag == 'supplied':
            reason = child.attrib.get('reason')
            cert = child.attrib.get('cert')
            sup = child.text or ''
            if reason == 'lost':
                text += f'[{sup}{"?" if cert == "low" else ""}]'
            elif reason == 'undefined':
                text += f'_[{sup}]_'
            elif reason == 'omitted':
                text += f'<{sup}>'
            elif reason == 'subaudible':
                text += f'({sup})'
            else:
                text += sup

        # Gaps
        elif tag == 'gap':
            # Ellipsis
            if child.attrib.get('reason') == 'ellipsis':
                text += '...'
            else:
                unit = child.attrib.get('unit')
                qty = child.attrib.get('quantity') or ''
                extent = child.attrib.get('extent')
                precision = child.attrib.get('precision')

                if unit == 'character':
                    if extent == 'unknown':
                        text += '[.?]'
                    elif precision == 'low':
                        text += f'[.{qty}]'
                    else:
                        text += '[' + '.' * int(qty or 0) + ']'
                elif unit == 'line':
                    if extent == 'unknown':
                        text += '(Lines: ? non transcribed)'
                    else:
                        text += f'(Lines: {qty} non transcribed)'

        # Deletions
        elif tag == 'del':
            inner = ''.join(child.itertext())
            if child.attrib.get('rend') == 'erasure':
                text += f'〚{inner}〛'
            else:
                text += inner

        # Additions
        elif tag == 'add':
            place = child.attrib.get('place')
            inner = child.text or ''
            if place == 'overstrike':
                text += f'《{inner}》'
            elif place == 'above':
                text += f'`{inner}´'
            elif place == 'below':
                text += f'/{inner}\\'
            else:
                text += inner

        # Corrections and regularizations
        elif tag == 'choice':
            corr = child.find('tei:corr', NS)
            sic = child.find('tei:sic', NS)
            reg = child.find('tei:reg', NS)
            orig = child.find('tei:orig', NS)
            if corr is not None and sic is not None:
                text += f'<{corr.text}|corr|{sic.text}>'
            elif reg is not None and orig is not None:
                text += f'<{orig.text}|reg|{reg.text}>'
            else:
                text += ''.join(child.itertext())

        # Highlighting
        elif tag == 'hi':
            rend = child.attrib.get('rend')
            inner = child.text or ''
            if rend == 'apex':
                text += f'{inner}(΄)'
            elif rend == 'supraline':
                text += f'{inner}¯'
            elif rend == 'ligature':
                text += f'{inner}\u0361'
            else:
                text += inner

        # Abbreviation expansions
        elif tag == 'expan':
            abbr = child.find('tei:abbr', NS)
            ex = child.find('tei:ex', NS)
            if abbr is not None and ex is not None:
                cert = ex.attrib.get('cert')
                text += f"{abbr.text}({ex.text}{'?' if cert=='low' else ''})"

        # Abbreviations, expansions, numerals
        elif tag in ('abbr', 'ex', 'num'):
            text += child.text or ''

        # Symbols
        elif tag == 'g':
            type_ = child.attrib.get('type')
            if type_:
                text += f'*{type_}*'

        # Superfluous letters
        elif tag == 'surplus':
            text += f'{{{child.text or ""}}}'

        # Notes
        elif tag == 'note':
            note = child.text or ''
            if note in ('!', 'sic', 'e.g.'):
                text += f'/*{note}*/'
            else:
                text += f'({note})'

        # Spaces on stone
        elif tag == 'space':
            unit = child.attrib.get('unit')
            qty = child.attrib.get('quantity')
            extent = child.attrib.get('extent')
            if unit == 'character':
                text += 'vac.?' if extent=='unknown' else f'vac.{qty}'
            elif unit == 'line':
                text += 'vac.?lin' if extent=='unknown' else f'vac.{qty}lin'

        # Word containers
        elif tag == 'w':
            text += format_leiden_text(child)

        # Fallback
        else:
            text += format_leiden_text(child)

        # Tail text
        if child.tail:
            text += child.tail

    return text


def extract_english_text(div, child_tag):
    """
    Extract and join text from all elements with the given child_tag that have xml:lang="en".
    This function works for translation and commentary sections.
    """
    texts = []
    if div is None:
        return ""
    for elem in div.findall(f".//tei:{child_tag}", NS):
        if elem.attrib.get("{http://www.w3.org/XML/1998/namespace}lang") == "en" and elem.text:
            texts.append(elem.text.strip())
    return "\n".join(texts)

def extract_apparatus_english(div):
    """
    Extract apparatus text from <app> elements in the apparatus section that have xml:lang="en".
    It searches for each <app> element with the attribute and extracts the text of its <note> child.
    """
    texts = []
    if div is None:
        return ""
    for app in div.findall(".//tei:app", NS):
        if app.attrib.get("{http://www.w3.org/XML/1998/namespace}lang") == "en":
            note = app.find("tei:note", NS)
            if note is not None and note.text:
                texts.append(note.text.strip())
    return "\n".join(texts)

def extract_bibliography(div):
    """
    Extract and join text from each <bibl> element.
    """
    texts = []
    if div is None:
        return ""
    for bibl in div.findall(".//tei:bibl", NS):
        if bibl.text:
            texts.append(bibl.text.strip())
    return "\n".join(texts)

st.title("ENCODE EpiDoc")

st.markdown("""
This application displays scholarly records of ancient Greek inscriptions.
Upload one or more TEI XML files to view key sections and information.
For the apparatus, translation, commentary, and bibliography sections only the English text is extracted and displayed as plain text.
For a case study download at least 5 XML files from the [Telamon project](https://telamon.uni-sofia.bg/) via the  **`download`** option in the end of description.   
""")

col1, col2 = st.columns(2)

with col1:
    uploaded_files = st.file_uploader("Upload your TEI XML files", type=["xml"], accept_multiple_files=True)

with col2:
    uploaded_images = st.file_uploader("Upload additional images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

image_data = {}
if uploaded_images:
    for img in uploaded_images:
        try:
            
            image_data[img.name] = {
                'data': img,
                'type': img.type
            }
        except Exception as e:
            st.warning(f"Could not process image {img.name}: {str(e)}")

if uploaded_files:
    viz_tab, query_tab, analytics_tab = st.tabs(["Data Visualization", "Search & Query", "Analytics"])
    
    all_data = []
    unique_types = set()
    unique_materials = set()
    unique_categories = set()
    parsed_files = []  
    
    for uploaded_file in uploaded_files:
        uploaded_file.seek(0)
        root, raw_xml = parse_tei(uploaded_file)
        if root is not None:
            # Store the parsed data
            parsed_files.append({
                'name': uploaded_file.name,
                'root': root,
                'raw_xml': raw_xml
            })
            ms_desc = root.find(".//tei:msDesc", NS)
            if ms_desc is not None:
                # Collect monument type
                object_type = get_text(ms_desc, ".//tei:objectType", lang="en")
                if object_type:
                    unique_types.add(object_type.lower())
                
                # Collect material
                material = get_text(ms_desc, ".//tei:material", lang="en")
                if material:
                    unique_materials.add(material.lower())
                
                # Collect category
                summary = ms_desc.find(".//tei:summary", NS)
                if summary is not None:
                    category = get_text(summary, ".//tei:seg", lang="en")
                    if category:
                        unique_categories.add(category.lower())
    
    with viz_tab:
        for file_data in parsed_files:
            st.markdown("---")
            st.header(f"Document: {file_data['name']}")
            
            root = file_data['root']
            raw_xml = file_data['raw_xml']

            # --- Extract key sections from the TEI header ---
            tei_header = root.find("tei:teiHeader", NS)
            file_desc = tei_header.find("tei:fileDesc", NS) if tei_header is not None else None
            title_stmt = file_desc.find("tei:titleStmt", NS) if file_desc is not None else None
            publication_stmt = file_desc.find("tei:publicationStmt", NS) if file_desc is not None else None
            source_desc = file_desc.find("tei:sourceDesc", NS) if file_desc is not None else None
            ms_desc = source_desc.find("tei:msDesc", NS) if source_desc is not None else None

            # Monument Title using the idno from publicationStmt.
            mon_id = get_text(publication_stmt, "tei:idno[@type='filename']")
            monument_title = f"Monument {mon_id}" if mon_id else "Monument"

            editors = title_stmt.findall("tei:editor/tei:persName", NS) if title_stmt is not None else []
            editor_names = [ed.text.strip() for ed in editors if ed.text]
            editor_str = ", ".join(editor_names) if editor_names else "Not available"

            # --- Extract information from physDesc ---
            phys_desc = ms_desc.find("tei:physDesc", NS) if ms_desc is not None else None
            object_desc = phys_desc.find("tei:objectDesc", NS) if phys_desc is not None else None
            support_desc = object_desc.find("tei:supportDesc", NS) if object_desc is not None else None
            support = support_desc.find("tei:support", NS) if support_desc is not None else None
            object_type = get_text(support, "tei:objectType", lang="en")
            material = get_text(support, "tei:material", lang="en")

            ms_identifier = ms_desc.find("tei:msIdentifier", NS) if ms_desc is not None else None
            alt_identifier = ms_identifier.find("tei:altIdentifier[@xml:lang='en']", NS) if ms_identifier is not None else None
            institution = ""
            repository = alt_identifier.find("tei:repository", NS) if alt_identifier is not None else None
            if repository is not None:
                ref = repository.find("tei:ref", NS)
                if ref is not None and ref.text:
                    institution = ref.text.strip()
            inventory = get_text(alt_identifier, "tei:idno")

            dimensions = support.find("tei:dimensions", NS) if support is not None else None
            height = dimensions.find("tei:height", NS).text.strip() if dimensions is not None and dimensions.find("tei:height", NS) is not None else ""
            width = dimensions.find("tei:width", NS).text.strip() if dimensions is not None and dimensions.find("tei:width", NS) is not None else ""
            depth = dimensions.find("tei:depth", NS).text.strip() if dimensions is not None and dimensions.find("tei:depth", NS) is not None else ""

            hand_desc = phys_desc.find("tei:handDesc", NS) if phys_desc is not None else None
            hand_note = hand_desc.find("tei:handNote", NS) if hand_desc is not None else None
            letter_size = hand_note.find("tei:height", NS).text.strip() if hand_note is not None and hand_note.find("tei:height", NS) is not None else ""

            layout_desc = object_desc.find("tei:layoutDesc", NS) if object_desc is not None else None
            layout = get_text(layout_desc, "tei:layout", lang="en")

            history = ms_desc.find("tei:history", NS) if ms_desc is not None else None
            provenance_found = None
            if history is not None:
                for prov in history.findall("tei:provenance", NS):
                    if prov.attrib.get("type", "") == "found":
                        provenance_found = prov
                        break
            find_place = ""
            if provenance_found is not None:
                seg = provenance_found.find("tei:seg[@xml:lang='en']", NS)
                if seg is not None and seg.text:
                    find_place = seg.text.strip()

            origin = ""
            if history is not None:
                origin_elem = history.find("tei:origin", NS)
                if origin_elem is not None:
                    orig_place = origin_elem.find("tei:origPlace", NS)
                    if orig_place is not None:
                        seg = orig_place.find("tei:seg[@xml:lang='en']", NS)
                        if seg is not None and seg.text:
                            origin = seg.text.strip()

            dating = ""
            if history is not None:
                origin_elem = history.find("tei:origin", NS)
                if origin_elem is not None:
                    orig_date = origin_elem.find("tei:origDate", NS)
                    if orig_date is not None:
                        seg = orig_date.find("tei:seg[@xml:lang='en']", NS)
                        if seg is not None and seg.text:
                            dating = seg.text.strip()

            ms_contents = ms_desc.find("tei:msContents", NS) if ms_desc is not None else None
            summary = ms_contents.find("tei:summary", NS) if ms_contents is not None else None
            inscription_category = ""
            if summary is not None:
                seg = summary.find("tei:seg[@xml:lang='en']", NS)
                if seg is not None and seg.text:
                    inscription_category = seg.text.strip()

            # --- Extract textual content from the body element ---
            text_elem = root.find("tei:text", NS)
            body_elem = text_elem.find("tei:body", NS) if text_elem is not None else None

            edition_div = None 
            apparatus_div = None
            translation_div = None
            commentary_div = None
            biblio_div = None

            if body_elem is not None:
                for div in body_elem.findall("tei:div", NS):
                    div_type = div.attrib.get("type", "")
                    if div_type == "edition" and div.attrib.get("{http://www.w3.org/XML/1998/namespace}lang") == "grc":
                        edition_div = div
                    elif div_type == "apparatus":
                        apparatus_div = div
                    elif div_type == "translation":
                        translation_div = div
                    elif div_type == "commentary":
                        commentary_div = div
                    elif div_type == "bibliography":
                        biblio_div = div

            if edition_div is not None:
                leiden_text = format_leiden_text(edition_div)
            else:
                leiden_text = "No Greek edition text available."

            apparatus_text = extract_apparatus_english(apparatus_div)
            translation_text = extract_english_text(translation_div, "seg")
            commentary_text = extract_english_text(commentary_div, "seg")
            bibliography_text = extract_bibliography(biblio_div)

            # --- Display the information ---
            st.header(monument_title)
            st.subheader("Monument Information")
            st.markdown(f"- **Editor(s):** {editor_str}")
            st.markdown(f"- **Type of monument:** {object_type if object_type else 'Not available'}")
            st.markdown(f"- **Material:** {material if material else 'Not available'}")
            st.markdown(f"- **Find place:** {find_place if find_place else 'Not available'}")
            st.markdown(f"- **Origin:** {origin if origin else 'Not available'}")
            st.markdown(f"- **Institution and Inventory:** {institution} No {inventory}")
            st.markdown(f"- **Dimensions:** Height {height} cm, width {width} cm, depth {depth} cm")
            st.markdown(f"- **Letter size:** Height {letter_size} cm")
            st.markdown(f"- **Layout description:** {layout if layout else 'Not available'}")
            st.markdown("- **Decoration description:** (appears to be blank)")
            
            st.subheader("Text and Dating Information")
            st.markdown(f"- **Category of inscription:** {inscription_category}")
            st.markdown(f"- **Dating criteria:** lettering")
            st.markdown(f"- **Date:** {dating if dating else 'Not available'}")

            st.subheader("Facsimiles and Images")
            
            matching_images = []
            if mon_id:
                for img_name, img_info in image_data.items():
                    
                    if mon_id.lower() in img_name.lower():
                        matching_images.append((img_name, img_info))
            
            if matching_images:
                st.markdown("**Uploaded Images:** *(Click thumbnails to view full size)*")
                cols = st.columns(3)  # Show max 3 images per row
                for idx, (img_name, img_info) in enumerate(matching_images):
                    try:
                        
                        with cols[idx % 3]:
                            st.image(img_info['data'], 
                                   caption=f"Uploaded: {img_name}", 
                                   width=150)
                            with st.expander("View full size"):
                                st.image(img_info['data'], 
                                       caption=f"Full size: {img_name}", 
                                       use_column_width=True)
                    except Exception as e:
                        st.warning(f"Could not display uploaded image {img_name}: {str(e)}")
            
            # Checks facsimile element in the XML structure for relevant data
            st.markdown("**XML-Referenced Facsimiles:** *(Click thumbnails to view full size)*")
            facsimiles = root.findall("tei:facsimile", NS)
            if facsimiles:
                image_urls = []
                for fac in facsimiles:
                    graphic = fac.find("tei:graphic", NS)
                    if graphic is not None and graphic.get("url"):
                        image_urls.append(graphic.get("url"))
                
                if image_urls:
                    cols = st.columns(3)  # Shows max 3 images per row
                    for idx, url in enumerate(image_urls):
                        try:
                            with cols[idx % 3]:
                                img_name = url.split('/')[-1]
                                if img_name in image_data:
                                    
                                    st.image(image_data[img_name]['data'], 
                                           caption=f"Facsimile {idx + 1}", 
                                           width=150)
                                
                                    with st.expander("View full size"):
                                        st.image(image_data[img_name]['data'], 
                                               caption=f"Facsimile {idx + 1} (Full size)", 
                                               use_column_width=True)
                                # If not found in uploads, try to load from URL/path, using correcting routes
                                elif url.startswith(('/', '\\', 'C:', 'D:')):
                                    try:
                                        with open(url, 'rb') as f:
                                            # Display thumbnail
                                            st.image(f, caption=f"Facsimile {idx + 1}", width=150)
                                            # Add expandable version
                                            with st.expander("View full size"):
                                                st.image(f, caption=f"Facsimile {idx + 1} (Full size)", 
                                                       use_column_width=True)
                                    except Exception as e:
                                        st.warning(f"Could not load facsimile from local path: {url}. Error: {str(e)}")
                                else:
                                    # Display thumbnail for remote URLs
                                    st.image(url, caption=f"Facsimile {idx + 1}", width=150)
                                    # Add expandable version
                                    with st.expander("View full size"):
                                        st.image(url, caption=f"Facsimile {idx + 1} (Full size)", 
                                               use_column_width=True)
                        except Exception as e:
                            st.warning(f"Could not load facsimile: {url}. Error: {str(e)}")
                else:
                    st.write("No facsimile references found in the document.")
            else:
                st.write("No facsimile elements found in the document.")

            st.subheader("Greek Text (Leiden+ formatted)")
            st.markdown("The following text is rendered from the edition (Greek) section:")
            st.text(leiden_text)

            st.subheader("Translation (English)")
            if translation_text:
                st.text(translation_text)
            else:
                st.write("No translation available.")

            st.subheader("Apparatus (English)")
            if apparatus_text:
                st.text(apparatus_text)
            else:
                st.write("No apparatus notes available.")

            st.subheader("Commentary (English)")
            if commentary_text:
                st.text(commentary_text)
            else:
                st.write("No commentary available.")

            st.subheader("Bibliography")
            if bibliography_text:
                st.text(bibliography_text)
            else:
                st.write("No bibliography available.")

            st.download_button(
                label="Download Original XML",
                data=raw_xml,
                file_name=mon_id + ".xml" if mon_id else "tei_document.xml",
                mime="text/xml"
            )

            
            monument_data = {
                'Title': monument_title,
                'Type': object_type if object_type else 'Not available',
                'Material': material if material else 'Not available',
                'Origin': origin if origin else 'Not available',
                'Date': dating if dating else 'Not available',
                'Category': inscription_category if inscription_category else 'Not available'
            }
            all_data.append(monument_data)

    with query_tab:
        st.header("Search & Query TEI Documents")
        
        # Dynamic search categories from loaded documents
        search_categories = {
            'Monument Types': sorted(list(unique_types)) if unique_types else ['No types found'],
            'Materials': sorted(list(unique_materials)) if unique_materials else ['No materials found'],
            'Categories': sorted(list(unique_categories)) if unique_categories else ['No categories found'],
            'Custom Search': ['custom']
        }
        
        # Show available options
        st.sidebar.subheader("Available Search Terms")
        if st.sidebar.checkbox("Show available terms"):
            st.sidebar.markdown("**Monument Types:**")
            st.sidebar.write(sorted(list(unique_types)))
            st.sidebar.markdown("**Materials:**")
            st.sidebar.write(sorted(list(unique_materials)))
            st.sidebar.markdown("**Categories:**")
            st.sidebar.write(sorted(list(unique_categories)))
        
        search_category = st.selectbox("Select search category", list(search_categories.keys()))
        
        if search_category == 'Custom Search':
            search_term = st.text_input("Enter custom search term")
        else:
            search_term = st.selectbox(f"Select {search_category}", search_categories[search_category])
            
        search_field = st.selectbox(
            "Select where to search",
            ["All Fields", "Monument Information", "Greek Text", "Translation", "Commentary", "Bibliography"]
        )
        
        st.info("💡 Note: Monument Information includes type, material, origin, etc.")

        if search_term and search_term != 'custom':
            search_term_lower = search_term.lower().strip()
            results = []  # Store all matches here
            
            for file_data in parsed_files:
                root = file_data['root']
                file_name = file_data['name']
                file_matches = []  # Store matches for this file
                
                # Extract monument information first
                tei_header = root.find("tei:teiHeader", NS)
                if tei_header is not None:
                    ms_desc = tei_header.find(".//tei:msDesc", NS)
                    if ms_desc is not None and search_field in ["All Fields", "Monument Information"]:
                        # Check type
                        object_type = get_text(ms_desc, ".//tei:objectType", lang="en")
                        if object_type and search_term_lower in object_type.lower():
                            file_matches.append(("Monument Type", object_type))
                        
                        # Check material
                        material = get_text(ms_desc, ".//tei:material", lang="en")
                        if material and search_term_lower in material.lower():
                            file_matches.append(("Material", material))
                        
                        # Check origin
                        origin = get_text(ms_desc, ".//tei:origin//tei:origPlace//tei:seg[@xml:lang='en']")
                        if origin and search_term_lower in origin.lower():
                            file_matches.append(("Origin", origin))
                
                # Search in text sections if needed
                body_elem = root.find("tei:text/tei:body", NS)
                if body_elem is not None:
                    for div in body_elem.findall("tei:div", NS):
                        div_type = div.attrib.get("type", "")
                        
                        # Search Greek Text
                        if div_type == "edition" and search_field in ["Greek Text", "All Fields"]:
                            if div.attrib.get("{http://www.w3.org/XML/1998/namespace}lang") == "grc":
                                text = format_leiden_text(div)
                                if text and search_term_lower in text.lower():
                                    file_matches.append(("Greek Text", text))
                        
                        # Search Translation
                        elif div_type == "translation" and search_field in ["Translation", "All Fields"]:
                            text = extract_english_text(div, "seg")
                            if text and search_term_lower in text.lower():
                                file_matches.append(("Translation", text))
                        
                        # Search Commentary
                        elif div_type == "commentary" and search_field in ["Commentary", "All Fields"]:
                            text = extract_english_text(div, "seg")
                            if text and search_term_lower in text.lower():
                                file_matches.append(("Commentary", text))
                        
                        # Search Bibliography
                        elif div_type == "bibliography" and search_field in ["Bibliography", "All Fields"]:
                            text = extract_bibliography(div)
                            if text and search_term_lower in text.lower():
                                file_matches.append(("Bibliography", text))
                
                
                if file_matches:
                    results.append({
                        'file_name': file_name,
                        'matches': file_matches
                    })
            
            # Only display results if any matches were found
            if results:
                st.subheader("Search Results")
                for result in results:
                    with st.expander(f"Results from {result['file_name']}"):
                        for section, content in result['matches']:
                            st.markdown(f"**Found in {section}:**")
                            st.text(content)
            else:
                st.info("No matches found for your search criteria.")

    with analytics_tab:
        st.header("Analytics & Visualizations")
        if all_data:
            df = pd.DataFrame(all_data)
            
            # Create a bar chart of monument types
            st.subheader("Distribution of Monument Types")
            type_counts = df['Type'].value_counts()
            fig_types = px.bar(
                x=type_counts.index, 
                y=type_counts.values,
                title="Monument Types Distribution",
                labels={'x': 'Type', 'y': 'Count'}
            )
            st.plotly_chart(fig_types)
            
            # Create a pie chart of materials
            st.subheader("Distribution of Materials")
            material_counts = df['Material'].value_counts()
            fig_materials = px.pie(
                values=material_counts.values,
                names=material_counts.index,
                title="Materials Distribution"
            )
            st.plotly_chart(fig_materials)
            
            # Create a timeline of monuments
            st.subheader("Timeline of Monuments")
            fig_timeline = px.scatter(
                df,
                x='Date',
                y='Category',
                color='Type',
                hover_data=['Title', 'Material'],
                title="Monuments Timeline"
            )
            st.plotly_chart(fig_timeline)
            
            
            st.subheader("Raw Data")
            st.dataframe(df)
        else:
            st.write("No data available for visualization. Please upload some XML files first.")
