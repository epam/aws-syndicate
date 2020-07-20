package com.syndicate.deployment.resolvers.credentials;

/**
 * Created by Oleksandr Onsha on 2019-08-15
 */
public abstract class AbstractChainedCredentialResolver implements IChainedCredentialsResolver {

	private IChainedCredentialsResolver nextResolver;

	@Override
	public IChainedCredentialsResolver getNextResolver() {
		return this.nextResolver;
	}

	@Override
	public void setNextResolver(IChainedCredentialsResolver resolver) {
		this.nextResolver = resolver;
	}

	@Override
	public boolean hasNextResolver() {
		return nextResolver != null;
	}
}
