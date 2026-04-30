# pdf-add-esign-field

A simple utility that adds blank e-signature fields to an existing PDF file.

Once a field is added, anyone with a free PDF reader (such as Adobe Acrobat Reader) can click the field and apply their digital signature using a digital token or certificate.

## What this tool does

- Opens an existing PDF
- Lets you draw a rectangle on the page to mark where a signature should go
- Saves a new PDF with that blank signature field embedded

That's it. This is a single-function utility.

## What this tool does NOT do

- Does **not** convert other file formats (Word, image, etc.) to PDF
- Does **not** edit, annotate, or modify any existing PDF content
- Does **not** sign the PDF - it only places an empty field that someone else signs later
- Does **not** apply any certificate or digital token itself

## Who is this for?

Individuals and small organizations that need documents signed repeatedly like board meeting minutes, invoices, contracts, approval forms and want a free, simple way to prepare those PDFs for digital signing.

## How to use

1. Launch the app
2. Click **Browse** to open a PDF file (on Mac, drag-and-drop onto the window is not currently working, use `Browse` button)
3. Navigate to the page where you want a signature field
4. Click and drag on the page preview to draw a rectangle where the signature should appear
5. Click **Add Field** and give the field a name
6. Repeat for any additional fields or pages
7. Click **Save PDF** to create a new PDF file with the signature field(s) embedded

The original PDF is not modified. A new file is saved alongside it.

## Running from source (Contributors or Linux & advanced users)

Make sure you have Python 3.8+ installed.

On **Windows**, you can also run:

```bat
run.bat
```

On **macOS**, you can also run:

```bash
./run.sh
```

If you don't care about creating a virtual environment or if the `run.sh` doesn't work for you (works on Mac but Linux tests are pending). 
```bash
pip install -r source/requirements.txt
python3 source/app.py
```
> Consider running above script in virtual environment. 


These launcher scripts create a virtual environment and install dependencies automatically.

---

For developer and build information, see [developer_notes.md](developer_notes.md).
