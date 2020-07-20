package com.syndicate.deployment.resolvers.credentials;

import com.syndicate.deployment.api.model.request.SyndicateCredentials;

/**
 * Created by Oleksandr Onsha on 2019-08-15
 */
public class CredentialResolverChain {

	private IChainedCredentialsResolver initialResolver;

	public CredentialResolverChain(IChainedCredentialsResolver initialResolver) {
		this.initialResolver = initialResolver;
	}

	public SyndicateCredentials resolveCredentialsInChain() {
		if (initialResolver == null) {
			return null;
		}
		IChainedCredentialsResolver resolver = initialResolver;
		SyndicateCredentials credentials = resolver.resolveCredentials();
		while (credentials == null && resolver.hasNextResolver()) {
			resolver = resolver.getNextResolver();
			credentials = resolver.resolveCredentials();
		}
		return credentials;
	}

}
