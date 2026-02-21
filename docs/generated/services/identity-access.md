# Identity Access Service endpoint reference

Source: `services/identity-access/src/main.py`

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/healthz` | `healthz` |
| `POST` | `/v1/auth/saml/acs` | `saml_acs` |
| `GET` | `/v1/auth/saml/login` | `saml_login` |
| `GET` | `/v1/auth/saml/metadata` | `saml_metadata` |
| `POST` | `/v1/auth/validate` | `validate_token` |
| `GET` | `/v1/scim/internal/roles/{user_id}` | `scim_get_roles` |
| `GET` | `/v1/scim/v2/Groups` | `scim_list_groups` |
| `POST` | `/v1/scim/v2/Groups` | `scim_create_group` |
| `PATCH` | `/v1/scim/v2/Groups/{group_id}` | `scim_patch_group` |
| `GET` | `/v1/scim/v2/Users` | `scim_list_users` |
| `POST` | `/v1/scim/v2/Users` | `scim_create_user` |
| `GET` | `/v1/scim/v2/Users/{user_id}` | `scim_get_user` |
| `PATCH` | `/v1/scim/v2/Users/{user_id}` | `scim_patch_user` |
| `GET` | `/version` | `version` |
