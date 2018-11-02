/*
 * Copyright 2018 EPAM Systems, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.syndicate.deployment.model.terraform;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.security.InvalidParameterException;

/**
 * Created by Oleksandr Onsha on 10/25/18
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class TerraformLambdaVpcConfig {

    @JsonProperty("subnet_ids")
    private String[] subnetIds;

    @JsonProperty("security_group_ids ")
    private String[] securityGroupIds;

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private TerraformLambdaVpcConfig vpcConfig = new TerraformLambdaVpcConfig();

        public Builder withSubnetIds(String[] subnetIds) {
            assertArray(subnetIds, "Subnet ids cannot be null or empty");
            vpcConfig.subnetIds = subnetIds;
            return this;
        }

        public Builder withSecurityGroupIds(String[] securityGroupIds) {
            assertArray(securityGroupIds, "Security group ids array cannot be null or empty");
            vpcConfig.securityGroupIds = securityGroupIds;
            return this;

        }

        public TerraformLambdaVpcConfig build() {
            assertArray(vpcConfig.subnetIds, "Subnet ids cannot be null or empty");
            assertArray(vpcConfig.securityGroupIds, "Security group ids array cannot be null or empty");
            return vpcConfig;
        }

        private void assertArray(String[] subnetIds, String errorMessage) {
            if (subnetIds == null || subnetIds.length == 0) {
                throw new InvalidParameterException(errorMessage);
            }
        }
    }

    public String[] getSubnetIds() {
        return subnetIds;
    }

    public String[] getSecurityGroupIds() {
        return securityGroupIds;
    }
}
