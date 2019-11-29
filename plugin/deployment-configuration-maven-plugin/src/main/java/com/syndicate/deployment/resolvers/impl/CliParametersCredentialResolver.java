package com.syndicate.deployment.resolvers.impl;

import com.syndicate.deployment.model.api.request.SyndicateCredentials;
import com.syndicate.deployment.resolvers.AbstractChainedCredentialResolver;

import java.security.InvalidParameterException;
import java.util.Objects;

/**
 * Resolves credentials passed as a cli parameter to plugin using -Dcredentials parameter.
 * Created by Oleksandr Onsha on 2019-08-15
 */
public class CliParametersCredentialResolver extends AbstractChainedCredentialResolver {

	private static final String CREDENTIALS_SEPARATOR = ":";

	private String credentialsCliParameter;

	public CliParametersCredentialResolver(String credentialsCliParameter) {
		this.credentialsCliParameter = credentialsCliParameter;
	}

	@Override
	public SyndicateCredentials resolveCredentials() {
		if (credentialsCliParameter != null) {
			String[] credentialsArray = credentialsCliParameter.split(CREDENTIALS_SEPARATOR);
			if (credentialsArray.length != 2) {
				throw new InvalidParameterException(String.format("Credentials are set up incorrect. " +
					"Please, use '%s' parameter as a separator for credentials. " +
					"Example: test_user@test.com%s123456", CREDENTIALS_SEPARATOR, CREDENTIALS_SEPARATOR));
			}
			String email = credentialsArray[0];
			Objects.requireNonNull(email, "Email cannot be empty.");
			String password = credentialsArray[1];
			Objects.requireNonNull(password, "Password cannot be empty.");
			return new SyndicateCredentials(email, password);
		}
		return null;
	}
}
