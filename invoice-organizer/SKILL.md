---
name: invoice-organizer
description: "Organize invoice files in a supplied folder by expense purpose, rename using purpose, amount, and seller, remove confirmed duplicates, and write count and amount summaries. Use for recurring invoice preparation for finance."
---

# Invoice organizer

When the user provides a folder for invoice organization, prepare the files for finance and create `统计.txt` in that folder. Work only in the supplied folder and its descendants. Do not upload invoice contents to external services.

## Identify and classify

- Inspect supported documents and images using available local tools. Extract the invoice's expense purpose (for example, 打车、代驾、餐饮、机票), amount, and seller/company name. Purpose means the business expense category, not the formal invoice type.
- Use the invoice's payable gross total (价税合计/含税总额) as the amount. Do not substitute tax-exclusive amount, unit price, invoice code, or invoice number.
- Classify from the invoice's description and line items. Use concise Chinese purpose labels. Do not infer a purpose from the seller alone when the document does not support it. For unclear purpose or amount, leave the file unchanged and record it as unresolved.
- Shorten the seller name by removing corporate suffixes such as 有限公司、股份有限公司、有限责任公司、集团有限公司. Preserve the distinctive name. Do not over-shorten distinct companies to the same label. If a reasonable company name cannot be identified, leave the file unchanged and record it as unresolved.
- Rename successfully identified files to `用途类型-¥金额-公司简写.原扩展名`, with amount formatted to two decimal places, e.g. `餐饮-¥128.00-示例餐饮.pdf`. Keep the original extension. Sanitize filesystem-invalid filename characters without changing the meaning.
- Never overwrite an existing file. If names collide, append a stable distinguishing value from the invoice (prefer invoice number; otherwise a short sequence suffix).

## Detect and remove duplicates

- First compare file contents (cryptographic hash) to find exact copies.
- Also identify duplicate invoices with matching invoice identifiers, or matching reliable invoice fields such as seller, invoice date, gross total, and line-item/details, even if scans, filenames, or file formats differ.
- Delete only duplicates that are confidently established. Keep one best-quality/most complete copy; remove the other copies. A similar amount or seller alone is insufficient. If uncertain, preserve the files and report them for review.
- Perform duplicate detection before renaming where practical. Do not treat an already-present `统计.txt` or unrelated files as invoices.

## Statistics and reporting

Write UTF-8 `统计.txt` to the supplied folder. Summarize retained, successfully identified invoices by expense purpose, including invoice count and total amount, then include an all-category total count and amount. Format each amount with `¥` and two decimal places. Example:

```text
餐饮：3 张，¥456.00
打车：2 张，¥78.50
合计：5 张，¥534.50
```

Do not include confirmed deleted duplicates in the totals. Add an unresolved section listing filenames and concise reasons for files that could not be identified safely. If duplicate candidates were preserved due to uncertainty, list them separately. Explain in the summary that totals cover retained, successfully identified invoices only. Ensure totals are calculated with decimal arithmetic, not binary floating point.

After processing, report counts of renamed invoices, confirmed duplicates deleted, and unresolved files. Do not claim deletion or successful extraction unless it occurred.
