-- Local development only: give the API roles a known password so Auth and PostgREST can connect.
alter role authenticator with password 'postgres';
alter role supabase_auth_admin with password 'postgres';
