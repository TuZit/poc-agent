# Requirement Summary

## Objective

Provide an e-commerce product management API so that products can be created,
updated, deleted and searched through a REST interface.

## Actors

- API consumer (authenticated end user or client system)
- Product manager (maintains the product catalogue)
- System administrator (manages authentication and access)

## Functional Requirements

1. Create product
2. Update product
3. Delete product
4. Search product
5. Authenticate every API request

## Product Attributes

- id
- name
- description
- price
- stock

## Non-Functional Requirements

- REST-style API with standard HTTP semantics
- Authentication required on every endpoint
- Input validation for product attributes (price >= 0, stock >= 0)

## Assumptions

- A single product catalogue is shared by all API consumers.
- Authentication is provided by an existing identity mechanism.
- Search covers product name and description.

## Open Questions

- Which pagination and sorting semantics should search support?
- Are soft deletes acceptable, or must deletion be permanent?
