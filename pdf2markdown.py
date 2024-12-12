import os
import concurrent.futures
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod


def convert_pdf_to_md(pdf_path, md_output_dir, max_retries=3):
    """
    Convert a PDF file to Markdown format and save it to the specified directory.

    Parameters:
        pdf_path (str): Absolute path to the PDF file to be processed.
        md_output_dir (str): Absolute path to the directory where the Markdown file will be saved.
        max_retries (int): Maximum number of retries for converting the PDF if an error occurs.

    Returns:
        None: If the conversion is successful.
        Prints the PDF file name if the conversion fails after maximum retries.
    """
    pdf_file_name = os.path.basename(pdf_path)  # Extract the file name
    name_without_suff = os.path.splitext(pdf_file_name)[0]  # Remove the file extension

    # Prepare environment
    local_image_dir = os.path.join(md_output_dir, "images")  # Image output directory
    os.makedirs(local_image_dir, exist_ok=True)
    os.makedirs(md_output_dir, exist_ok=True)
    image_dir = os.path.basename(local_image_dir)  # Relative path for images in Markdown

    # Initialize writers
    image_writer = FileBasedDataWriter(local_image_dir)
    md_writer = FileBasedDataWriter(md_output_dir)

    # Initialize reader
    reader = FileBasedDataReader("")

    # Retry logic
    for attempt in range(max_retries):
        try:
            # Read the PDF bytes
            pdf_bytes = reader.read(pdf_path)
            
            # Create Dataset Instance
            ds = PymuDocDataset(pdf_bytes)

            # Inference and processing
            if ds.classify() == SupportedPdfParseMethod.OCR:
                infer_result = ds.apply(doc_analyze, ocr=True)
                pipe_result = infer_result.pipe_ocr_mode(image_writer)
            else:
                infer_result = ds.apply(doc_analyze, ocr=False)
                pipe_result = infer_result.pipe_txt_mode(image_writer)

            # Dump Markdown file
            pipe_result.dump_md(md_writer, f"{name_without_suff}.md", image_dir)
            
            # If successful, exit the function
            return

        except Exception as e:
            # Log the error for debugging (optional, can be removed in production)
            print(f"Attempt {attempt + 1} failed for file {pdf_file_name}: {e}")

    # If all retries fail, notify the user
    print(f"Failed to convert {pdf_file_name} to Markdown after {max_retries} retries.")


def batch_convert_pdfs_to_md(pdf_folder, md_output_dir, max_retries=3, max_workers=8):
    """
    Convert all PDF files in a folder to Markdown format using multi-threading.

    Parameters:
        pdf_folder (str): Absolute path to the folder containing PDF files.
        md_output_dir (str): Absolute path to the directory where Markdown files will be saved.
        max_retries (int): Maximum number of retries for each PDF conversion.
        max_workers (int): Maximum number of threads to use for parallel processing.

    Returns:
        None
    """
    # Ensure the output directory exists
    os.makedirs(md_output_dir, exist_ok=True)

    # Get a list of all PDF files in the folder
    pdf_files = [os.path.join(pdf_folder, f) for f in os.listdir(pdf_folder) if f.endswith('.pdf')]

    if not pdf_files:
        print("No PDF files found in the specified folder.")
        return

    # Use ThreadPoolExecutor for multi-threading
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks for each PDF file
        futures = {
            executor.submit(convert_pdf_to_md, pdf_file, md_output_dir, max_retries): pdf_file
            for pdf_file in pdf_files
        }

        for future in concurrent.futures.as_completed(futures):
            pdf_file = futures[future]
            try:
                future.result()  # Wait for the task to complete
            except Exception as e:
                print(f"❌Error processing file {pdf_file}: {e}")

    print("Batch conversion completed.")


if __name__ == "__main__":
    # Example usage
    pdf_folder = "/data/lyc/papers/ICLR_2024/pdf"  # Replace with the folder containing PDF files
    md_output_dir = "/data/lyc/papers/ICLR_2024/md"  # Replace with the output folder for Markdown files
    max_retries = 3  # Maximum retries for each PDF conversion
    max_workers = 1  # Number of threads for parallel processing

    batch_convert_pdfs_to_md(pdf_folder, md_output_dir, max_retries, max_workers)
