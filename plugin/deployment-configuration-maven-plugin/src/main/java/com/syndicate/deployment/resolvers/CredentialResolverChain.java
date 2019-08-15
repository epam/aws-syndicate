package com.syndicate.deployment.resolvers;

import com.syndicate.deployment.model.api.request.Credentials;

/**
 * Created by Oleksandr Onsha on 2019-08-15
 */
public class CredentialResolverChain {

	private IChainedCredentialsResolver initialResolver;

	public CredentialResolverChain(IChainedCredentialsResolver initialResolver) {
		this.initialResolver = initialResolver;
	}

	public Credentials resolveCredentialsInChain() {
		if (initialResolver == null) {
			return null;
		}
		IChainedCredentialsResolver resolver = initialResolver;
		Credentials credentials = resolver.resolveCredentials();
		while (credentials == null || !resolver.hasNextResolver()) {
			resolver = resolver.getNextResolver();
			credentials = resolver.resolveCredentials();
		}
		return credentials;
	}

}
