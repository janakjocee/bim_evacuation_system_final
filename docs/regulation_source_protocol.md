# Regulation Source and Applicability Protocol

Status date: 16 August 2026

## Permitted Research Use

Use the official GOV.UK publication page as the canonical source for Approved
Document B:

- https://www.gov.uk/government/publications/fire-safety-approved-document-b

GOV.UK pages normally identify Crown copyright and Open Government Licence
terms, subject to stated exceptions and third-party material. Retain attribution,
the source URL and the document's own copyright/licence notice. Do not assume
that every diagram, standard extract or third-party item inside a government PDF
has identical reuse terms.

The local file
`Practical_ADB_Volume2_Regulation_Input_for_BIM_Evacuation.txt` is a curated
academic screening input. It is not an official replacement for the complete
document and must not be described as legal advice or professional approval.

## Evidence Record

For every evaluated regulation upload, record:

1. Exact uploaded filename and SHA-256.
2. Official source URL.
3. Download/access date.
4. Jurisdiction and building scope.
5. Edition, incorporated amendments and correction status.
6. Relevant commencement date and transitional provisions.
7. Clauses selected for the prototype and why they are applicable.
8. Unsupported clauses or tables that the parser did not operationalise.
9. Reviewer identity/reference for any professional applicability decision.

The application now exports items 1-5 when supplied. Items 6-9 remain human
review evidence and must not be inferred automatically.

## Date Boundary

The collated GOV.UK document can show amendments for multiple effective dates.
As at 16 August 2026, the government publication describes second-stair
provisions as coming into force on 30 September 2026 and later fire-resistance
classification changes as coming into force on 2 September 2029. Their presence
in a collated PDF does not make them applicable before their commencement date,
and transitional arrangements can affect a particular project.

The prototype does not implement legal temporal reasoning. A reviewer must
select the applicable clause set before interpreting a result.

## Correct Demonstration Claim

Use this wording:

> The prototype extracts candidate constraints and retrieves traceable evidence
> from an uploaded regulation document. Supported values can drive deterministic
> screening checks. Legal applicability and compliance remain outside the
> prototype and require a competent reviewer.

Do not say that the system reads all UK fire law, proves Approved Document B
compliance, or replaces building-control and fire-engineering assessment.
