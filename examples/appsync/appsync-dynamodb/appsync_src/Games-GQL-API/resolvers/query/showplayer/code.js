import * as ddb from '@aws-appsync/utils/dynamodb';
import { util } from '@aws-appsync/utils';

export function request(ctx) {
    return {
        operation: "Query",
        query: {
            expression: 'PK = :pk and begins_with(SK, :sk)',
            expressionValues: util.dynamodb.toMapValues({
                ":pk": ctx.args.game_name,
                ':sk': ctx.args.email
            })
        }
    }
}


export function response(ctx) {
    if (ctx.error) {
        return util.error(ctx.error.message, ctx.error.type);
    }
    if (!ctx.result || !ctx.result.items || ctx.result.items.length === 0) {
        return util.error("Player not found.", "NotFoundError");
    }

    return ctx.result.items[0];
}