package com.syndicate.deployment.resolvers.credentials;

import com.syndicate.deployment.api.model.request.SyndicateCredentials;

/**
 * Created by Oleksandr Onsha on 2019-08-15
 */
public interface IChainedCredentialsResolver {

	SyndicateCredentials resolveCredentials();

	void setNextResolver(IChainedCredentialsResolver resolver);

	IChainedCredentialsResolver getNextResolver();

	boolean hasNextResolver();
}
