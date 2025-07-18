import re

def get_sku_or_ean(text):
    match = re.search(r'\b(?:sku|ean)\s*:\s*(.+)', text, re.IGNORECASE)
    if match:
        print(f"Extracted SKU/EAN:{match.group(1).strip()}")
        return match.group(1).strip()
    else:
        print("No SKU or EAN found in the text.")
        # If no match, return a default value or handle it as needed
    return "N/A"


get_sku_or_ean("the thing is actually SKU: 12345")  # Example usage
get_sku_or_ean("EaN: 67890")  # Example usage
get_sku_or_ean("eAN: 2325")  # Example usage
get_sku_or_ean("tortafrita")  # Example usage
get_sku_or_ean("the PLU: 435313 ean: 67890")  # Example usage