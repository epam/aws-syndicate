import { util } from '@aws-appsync/utils';

export function request(ctx) {
    ctx.stash['game_name'] = ctx.args.name;
    return {
        operation: "Query",
        query: {
            "expression": "PK = :pk",
            "expressionValues": {":pk": { S: ctx.args.name } }
        }
    }
}

export function response(ctx) {
    if (ctx.error) {
        return util.error(ctx.error.message, ctx.error.type);
    }
    if (!ctx.result || !ctx.result.items || ctx.result.items.length === 0) {
        return util.error("Game not found.", "NotFoundError");
    }
    let game = {};
    const players = [];
    const gameName = ctx.stash.game_name;

    for (var item of ctx.result.items) {
        if (item.SK === gameName) {
            game = { ...item, name: gameName };
        } else {
            players.push(item);
        }
    }

    game.players = players;
    return game;
}
