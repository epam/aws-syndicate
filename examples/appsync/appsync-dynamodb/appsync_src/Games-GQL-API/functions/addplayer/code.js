import { util } from '@aws-appsync/utils';

export function request(ctx) {
    const items = ctx.prev.result.items;

    if (!items || items.length === 0) {
        return util.error("Game not found.", "NotFoundError");
    }

    const id = ctx.stash.id;
    return {
        operation: "PutItem",
        key: util.dynamodb.toMapValues({
            PK: ctx.args.input.game_name,
            SK: `${ctx.args.input.email}#${ctx.args.input.game_name}`
        }),
        attributeValues: util.dynamodb.toMapValues({
            id: id,
            email: ctx.args.input.email,
            nic: ctx.args.input.nic,
            personal_info: ctx.args.input.personal_info
        }),
        condition: {
            expression: "attribute_not_exists(PK) and attribute_not_exists(SK)"
        }
    };
}

export function response(ctx) {
    if (ctx.error) {
        return util.error(ctx.error.message, ctx.error.type);
    }
    return ctx.result;
}
