# CVP Natural-Language Query Workflow

## 1. Classify the Question

Convert the user request into a small query contract:

- entity or endpoint candidates
- filters, search text, and exact identifiers
- output fields needed for the answer
- join keys or referenced IDs
- whether live data access is required or a dry-run plan is enough

If the user asks for a report, define both the final columns and the output grain before querying. Examples: one row per program, one row per Media object, or one row per MediaFile. The grain determines which parent fields must be repeated and how child objects should be represented.

## 2. Resolve Endpoint and Field Semantics

Use `references/service-map.json` for seeded endpoint URLs, then verify any uncertain behavior with CVP docs.

Prefer this lookup sequence:

1. endpoint page
2. object page
3. Data Service selection/query parameter pages
4. schema history or release notes only when behavior appears version-sensitive

Do not assume field names from Console labels. Map UI labels to API fields through object documentation or returned schema/data.

## 3. Build the First Query

Use the narrowest query that can answer the first part of the question.

Recommended order:

1. exact ID or GUID lookup when the user supplied one
2. exact field lookup where documented
3. `q` search for human-entered title/text when exact lookup is not available
4. broader scan only after reporting why the narrower query failed

Always include the fields needed for:

- user-visible answer
- source record identity
- next-hop joins
- troubleshooting, such as owner/account and timestamps

## 4. Execute Safely

Before a live request, check:

- URL is a CVP endpoint expected for the task
- method is `GET`
- auth comes from environment variables or explicit runtime headers
- query does not request excessive fields or unbounded pages unless the user needs a full export

Use `scripts/cvp_query.py get` for simple GETs. For complex pagination or exports, create a task-local script in the workspace, not inside the skill.

When CVP returns JSON, inspect the body for exception payloads such as `isException: true` even when the HTTP status is 200.

## 5. Cross-Reference IDs

Maintain a join table with these columns while working:

- `source_endpoint`
- `source_id`
- `source_label`
- `reference_field`
- `target_endpoint`
- `target_id`
- `target_label`
- `status`

Statuses:

- `resolved`: exactly one target record found
- `missing`: no target record found
- `ambiguous`: multiple target records found
- `unverified`: relationship inferred but not confirmed

Never collapse unresolved IDs into a clean answer. Surface them as data quality or permission gaps.

## 6. Pagination and Counts

If the question depends on complete counts, do not rely on the first page unless the endpoint docs or response metadata confirms the total. Capture the page size, next-page marker, or total field when present. If pagination behavior is not confirmed, state that the count is page-limited.

For large CVP exports, keep page sizes conservative and endpoint-compatible. If rate limiting or transient server errors occur, use retry/backoff behavior and preserve partial outputs separately from final outputs.

## 7. Answer From Evidence

Answer in this order:

1. conclusion
2. evidence table or compact list
3. endpoints and filters used
4. unresolved references or caveats
5. doc citations used to build the query

Use clear labels:

- `Observed`: directly returned by CVP data
- `Inferred`: derived from joins or field interpretation
- `Not verified`: blocked by missing docs, permissions, pagination, or absent fields

## 8. Common Patterns

### Find a Media item by title and inspect metadata

1. Search `Media` with `q` or an exact title field if documented.
2. Return identity fields plus the requested metadata fields.
3. If multiple matches appear, ask the user to choose or disambiguate by owner/account/date.

### Explain file-level state for a title

1. Resolve the `Media` record first.
2. Use the Media-to-MediaFile relationship documented for the service, or query `MediaFile` by the documented media reference field.
3. Join Media display fields to MediaFile technical fields.

### Audit missing or broken references

1. Query source records with the reference field included.
2. Deduplicate target IDs.
3. Resolve target IDs against the owning endpoint.
4. Report missing and ambiguous references separately from good records.

### Build a user-ready report

1. Confirm columns and row grain.
2. Fetch minimal fields.
3. Resolve labels for foreign IDs.
4. Save a CSV only if requested.
5. Include endpoint and filter metadata in the final summary.

For child-object reports, prefer one row per child record with parent fields repeated. Avoid pipe-joined multi-value summary cells when the user expects values to be readable in spreadsheet cells.

For Excel-readable CSVs:

- flatten nested child object fields into individual columns where practical
- use stable prefixes such as `program_`, `media_`, and `mediaFile_`
- preserve empty values as blank cells, not placeholder delimiters
- normalize embedded newlines when multiline payloads would make the sheet hard to scan
- write UTF-8 with BOM when the CSV is intended to be opened directly in Excel

Treat "return everything" exports as sensitive. CVP file payloads can include URLs, paths, transfer settings, or credential-like fields. Keep raw JSON/CSV artifacts internal unless explicitly sanitized.
