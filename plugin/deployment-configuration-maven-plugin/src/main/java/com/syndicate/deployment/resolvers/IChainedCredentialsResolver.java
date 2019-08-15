package com.syndicate.deployment.resolvers;

import com.syndicate.deployment.model.api.request.Credentials;

/**
 * Created by Oleksandr Onsha on 2019-08-15
 */
public interface IChainedCredentialsResolver {

	Credentials resolveCredentials();

	void setNextResolver(IChainedCredentialsResolver resolver);

	IChainedCredentialsResolver getNextResolver();

	boolean hasNextResolver();
}
