# appsync + dynamodb example

The project is an example of the integration of AWS AppSync with DynamoDB

## AppSync API key features

### name: 
`Games-GQL-API`  

### primary authorization mode
`API_KEY`

### data sources
`gamesDB` of type `AMAZON_DYNAMODB`

### resolvers
kind `UNIT` type `Mutation` field `addGame` runtime `VTL` data source `gamesDB`  
kind `PIPELINE` type `Mutation` field `addPlayer` runtime `VTL`  functions `[getGameItem, addPlayer]`  
kind `UNIT` type `Query` field `showGame` runtime `JS` data source `gamesDB`  
kind `UNIT` type `Query` field `showPlayer` runtime `JS` data source `gamesDB` 

### functions
name `getGameItem` runtime `VTL` data source `gamesDB`  
name `addPlayer` runtime `JS` data source `gamesDB`

### CW logs configuration
enabled `true` log level `ERROR`

## Queries
### Prerequisites
 - Any client that supports GraphQL queries(Postman, Altair GraphQL Client) configured to query GraphQL endpoint
 - Auth type - `API KEY`, key name - `x-api-key`

**Notes**  
  GraphQL endpoint and value of API_KEY can be found in the AppSync API settings after deployment 

### type `Mutation` field `addGame`
Query
```buildoutcfg
mutation addGame($input: AddGameInput!) {
  addGame(input: $input) {
    id
  }
}
```
Query variables
```json
{
    "input": {
        "name": "test",
        "mode": "singlePlayer"
    }
}
```
#### Expected response
```buildoutcfg
{
    "data": {
        "addGame": {
            "id": "//uuidv4"
        }
    }
}
```
---

### type `Mutation` field `addPlayer`
Query
```buildoutcfg
mutation addPlayer($input: AddPlayerInput!) {
  addPlayer(input: $input) {
    id
  }
}
```
Query variables
```json
{
    "input": {
        "game_name": "test",
        "email": "test@example.com",
        "nic": "test_nic",
        "personal_info": "{\"age\": 22, \"country\": \"Ukraine\", \"phone_number\": \"+380681111111\"}"
    }
}
```
#### Expected response
```buildoutcfg
{
    "data": {
        "addPlayer": {
            "id": "//uuidv4"
        }
    }
}
```

#### Expected response in case of an attempt to add a player to a non-existent game
**Notes** 
`ErrorType` and `message` for this case are defined in the function `addPlayer`

```buildoutcfg
{
    "data": {
        "addPlayer": null
    },
    "errors": [
        {
            "path": [
                "addPlayer"
            ],
            "data": null,
            "errorType": "NotFoundError",
            "errorInfo": null,
            "locations": [
                {
                    "line": 2,
                    "column": 3,
                    "sourceName": null
                }
            ],
            "message": "Game not found."
        }
    ]
}
```
---

### type `Query` field `showGame`
Query
```buildoutcfg
query showGame($name: String!)  {
   showGame(name: $name){
    players {
        id
        nic
        email
        personal_info {
            age
            country
            phone_number
        }
      }
    id
    name
  }
}
```
Query variables
```json
{
    "name": "test"
}
```
#### Expected response
```buildoutcfg
{
    "data": {
        "showGame": {
            "players": [
                {
                    "id": "//uuidv4",
                    "nic": "test_nic",
                    "email": "test@example.com",
                    "personal_info": {
                        "age": 22,
                        "country": "Ukraine",
                        "phone_number": "+380681111111"
                    }
                }
            ],
            "id": "//uuidv4",
            "name": "test"
        }
    }
}
```
---

### type `Query` field `showPlayer`
Query
```buildoutcfg
query showPlayer($game_name: String!, $email: AWSEmail!)  {
   showPlayer(game_name: $game_name, email: $email){
        id
        nic
        email
        personal_info {
            age
            country
            phone_number
        }
   }
}
```
Query variables
```json
{
    "game_name": "test",
    "email": "test@example.com"
}
```
#### Expected response
```buildoutcfg
{
    "data": {
        "showPlayer": {
            "id": "//uuidv4",
            "nic": "test_nic",
            "email": "test@example.com",
            "personal_info": {
                "age": 22,
                "country": "Ukraine",
                "phone_number": "+380681111111"
            }
        }
    }
}
```
---

## Deployment from scratch
1. Fill in the file `syndicate.yml` with the real data
2. Set up the environment variable `SDCT_CONF` so it points to `.syndicate-config-appsync-dynamodb`
3. Run the command `syndicate build && syndicate deploy`

