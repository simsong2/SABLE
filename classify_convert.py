#Name:            classify_convert.py
#Purpose:         Convert PDFs that have been manually classified into the /data/pos_pdf/ and /data/neg_pdf/ folders to TXT format and extract metadata for use with classify_model.py
#Data Layout:     See README.md
#Python Version:  2

import codecs
import os
import re
import string

#Global variables
stop_words = set([])
probflag = 0

#Name:       convert_pdf_xml
#Arguments:  pdffile (location of PDF file)
#            xmlfile (location of XML output)
#Purpose:    Convert a PDF file to XML format

def convert_pdf_xml(pdffile, xmlfile):
    global probflag
    try:
        #The pdf2txt.py program comes with the PDFMiner module
        os.system("pdf2txt.py -o " + xmlfile + " -t xml " + pdffile)
    except PDFTextExtractionNotAllowed:
        #Exception indicates text cannot be extracted from the PDF
        #The problem PDFs will be moved to the /data/pos_problem/ and /data/neg_problem/ folders for inspection
        probflag = 1
    return

#Name:       match_page
#Arguments:  line (line of text from XML file)
#Purpose:    Match line to an XML page tag

def match_page(line):
    return re.search(r"<page id=\"(\d+)\"", line)

#Name:       match_textbox
#Arguments:  line (line of text from XML file)
#Purpose:    Match line to an XML textbox tag

def match_textbox(line):
    return re.search(r"<textbox id=\"(\d+)\"", line)

#Name:       match_textline
#Arguments:  line (line of text from XML file)
#Purpose:    Match line to an XML textline tag

def match_textline(line):
    return re.search(r"<textline", line)

#Name:       match_text
#Arguments:  line (line of text from XML file)
#Purpose:    Match line to an XML text tag

def match_text(line):
    return re.search(r"<text.*font=\"(.*)\".*bbox=\"([0-9]+\.[0-9]+),([0-9]+\.[0-9]+),([0-9]+\.[0-9]+),([0-9]+\.[0-9]+)\".*size=\"([0-9]+\.[0-9]+)\">(.*)</text>", line)

#Name:       clean_char
#Arguments:  old (character)
#Purpose:    Remove foreign accent from character

def clean_char(old):
    if len(old) > 1:
        new = " "
    else:
        o = ord(old)
        if (192 <= o <= 198) or (224 <= o <= 230):
            new = "a"
        elif o == 199 or o == 231:
            new = "c"
        elif (200 <= o <= 203) or (232 <= o <= 235):
            new = "e"
        elif (204 <= o <= 207) or (236 <= o <= 239):
            new = "i"
        elif o == 209 or o == 241:
            new = "n"
        elif (210 <= o <= 214) or (242 <= o <= 246):
            new = "o"
        elif (217 <= o <= 220) or (249 <= o <= 252):
            new = "u"
        elif o == 221 or o == 253 or o == 255:
            new = "y"
        elif o >= 128:
            new = " "
        else:
            new = old
    return new

#Name:       get_chars
#Arguments:  xmlfile (location of XML file)
#Purpose:    Extract the character values, coordinates, hierarchy, and font information from XML file

def get_chars(xmlfile):
    chars = []
    page = 0
    textbox = 0
    textline = 0
    f = codecs.open(xmlfile, "rU", encoding="utf8")
    for l in f:
        line = l.strip()
        pagematch = match_page(line)
        textboxmatch = match_textbox(line)
        textlinematch = match_textline(line)
        textmatch = match_text(line)
        if pagematch:
            page = int(pagematch.group(1))
        elif textboxmatch:
            textline = 0
            textbox = int(textboxmatch.group(1))
        elif textlinematch:
            textline = textline + 1
        elif textmatch:
            font = textmatch.group(1)
            x1 = float(textmatch.group(2))
            y1 = float(textmatch.group(3))
            x2 = float(textmatch.group(4))
            y2 = float(textmatch.group(5))
            size = float(textmatch.group(6))
            value = clean_char(textmatch.group(7))
            chars.append((page, textbox, textline, x1, y1, x2, y2, size, font, value))
    f.close()
    return chars

#Name:       clean_meta
#Arguments:  text (string)
#Purpose:    Process string of text and check each word

def clean_meta(text):
    text = text.lower()
    text = re.sub("\t+", " ", text)
    text = re.sub("\n+", " ", text)
    text = re.sub("[0-9]+", "", text)
    text = re.sub("-+", " ", text)
    text = re.sub(" +", " ", text)
    text_clean = []
    text = text.split(" ")
    for word in text:
        word = word.strip()
        if word not in stop_words:
            text_clean.append(word)
    text_clean = " ".join(text_clean)
    return text_clean

#Name:       write_meta
#Arguments:  chars (list of tuples)
#            metafile (location of TXT metafile)
#Purpose:    Construct words character by character

def write_meta(chars, metafile):
    meta = []
    chars = sorted(chars, key = lambda z: (z[0], z[1], z[2], -z[4], z[3]))
    
    page_cur = chars[0][0]
    textbox_cur = chars[0][1]
    textline_cur = chars[0][2]

    for char in chars:
        space_flag = 0
        page_new = char[0]
        textbox_new = char[1]
        textline_new = char[2]
        if page_new != page_cur:
            page_cur = page_new
            space_flag = 1
        if textbox_new != textbox_cur:
            textbox_cur = textbox_new
            space_flag = 1
        if textline_new != textline_cur:
            textline_cur = textline_new
            space_flag = 1
        if space_flag == 1:
            meta.append(" ")
        if char[9] in string.punctuation:
            meta.append(" ")
        else:
            meta.append(char[9])

    meta = "".join(meta)
    meta_clean = clean_meta(meta)
    f = codecs.open(metafile, "w")
    f.write(meta_clean)
    f.close()
    return

#Name:       create_files
#Arguments:  clss ("pos" or "neg")
#            docname (document name)
#Purpose:    Convert a PDF document of a given class to TXT format

def create_files(clss, docname):
    pdffile  = "/data/" + clss + "_pdf/"  + docname + ".pdf"
    xmlfile  = "/data/" + clss + "_xml/"  + docname + ".xml"
    metafile = "/data/" + clss + "_meta/" + docname + ".txt"

    newflag = 0
    global probflag
    probflag = 0
    chars = []

    if not os.path.isfile(metafile):
        newflag = 1
        convert_pdf_xml(pdffile, xmlfile)
        if not os.path.isfile(xmlfile):
            probflag = 1
        elif os.stat(xmlfile).st_size == 0:
            probflag = 1
        if probflag == 0:
            chars = get_chars(xmlfile)
            if len(chars) == 0:
                probflag = 1
    if newflag == 1 and probflag == 0:
        write_meta(chars, metafile)
        if os.path.isfile(xmlfile):
            os.remove(xmlfile)
    elif newflag == 1 and probflag == 1:
        if os.path.isfile(xmlfile):
            os.remove(xmlfile)
        if os.path.isfile(metafile):
            os.remove(metafile)
        newpdffile = "/data/" + clss + "_problem/" + docname + ".pdf"
        os.system("mv " + pdffile + " " + newpdffile)

    if newflag == 1 and probflag == 0:
        print(docname)
    elif newflag == 1 and probflag == 1:
        print("!!! PROBLEM !!!", docname)
    return

def main():
    lng  = "english"
    clss = "pos"

    stop_words_list = []
    f = codecs.open("stop_" + lng + ".txt", "rU")
    for w in f:
        if w.strip() != "":
            stop_words_list.append(w)
    f.close()
    global stop_words
    stop_words = set(stop_words_list)

    print("\n*****  " + clss + "  *****\n")
    pdfs = sorted(os.listdir("/data/" + clss + "_pdf"))
    for pdf in pdfs:
        pdfmatch = re.search(r"(\S+)\.pdf$", pdf)
        if pdfmatch:
            docname = pdfmatch.group(1)
            create_files(clss, docname)
    print("")
    return

if __name__ == "__main__":
    main()
