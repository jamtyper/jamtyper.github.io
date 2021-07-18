# jamtyper

Live music coding with your friends

## PUT on the json

```sh
curl -X PUT -d '{"key": "value"}' https://jamtyper-969f2-default-rtdb.firebaseio.com/songs/data.json
```

## Rules

Set the following rules for create only, no UPDATE and no DELETE

```json
{
  "rules": {
    ".read": true,
    ".write": "!data.exists()"
  }
}
```
